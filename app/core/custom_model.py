import torch
import torch.nn as nn
import numpy as np
from typing import Sequence, Union, Tuple, Optional
from monai.networks.blocks.convolutions import Convolution
from monai.networks.layers.factories import Act, Norm
from monai.networks.layers.utils import get_act_layer, get_norm_layer

# Try importing pennylane, but handle if missing
try:
    import pennylane as qml
    HAS_PENNYLANE = True
except ImportError:
    HAS_PENNYLANE = False
    qml = None

# --- Quantum Config ---
n_qubits = 10
n_layers = 6 

if HAS_PENNYLANE:
    dev = qml.device("default.qubit", wires=n_qubits)

    @qml.qnode(dev, interface="torch")
    def quantum_circuit(inputs, weights):
        qml.templates.AngleEmbedding(inputs, wires=range(n_qubits))
        qml.templates.StronglyEntanglingLayers(weights, wires=range(n_qubits))
        return [qml.expval(qml.PauliZ(wires=i)) for i in range(n_qubits)]

class QuantumLayer(nn.Module):
    def __init__(self, n_qubits, n_layers):
        super().__init__()
        if not HAS_PENNYLANE:
            raise ImportError("PennyLane is required for QuantumLayer. Please 'pip install pennylane'.")
            
        weight_shapes = {"weights": (n_layers, n_qubits, 3)}
        self.q_layer = qml.qnn.TorchLayer(quantum_circuit, weight_shapes)
    
    def forward(self, x):
        return self.q_layer(x)

class ParallelQuantumBottleneck(nn.Module):
    def __init__(self, in_channels, out_channels, target_spatial_shape):
        super().__init__()
        self.target_spatial_shape = target_spatial_shape
        self.flat_out_dim = out_channels * np.prod(target_spatial_shape)
        
        # 1. Classical Down-Projection (Squeeze)
        self.pool = nn.AdaptiveAvgPool3d((1, 1, 1)) # Forces size to (Batch, Ch, 1, 1, 1)
        self.fc_down = nn.Linear(in_channels, n_qubits)
        
        # 2. Parallel Quantum Layers
        self.q_layer1 = QuantumLayer(n_qubits, n_layers)
        self.q_layer2 = QuantumLayer(n_qubits, n_layers)
        
        # 3. Up-Projection
        # Input: n_qubits * 2 (concatenated outputs)
        self.fc_up = nn.Linear(n_qubits * 2, self.flat_out_dim)
        
    def forward(self, x):
        b = x.shape[0]
        
        # Flatten: (Batch, 384, D, H, W) -> (Batch, 384)
        x_flat = self.pool(x).view(b, -1)
        
        # Squeeze to Quantum Dim: (Batch, 10)
        # Using Sigmoid * PI for AngleEmbedding
        q_in = torch.sigmoid(self.fc_down(x_flat)) * np.pi
        
        # Run Parallel Blocks
        q_out1 = self.q_layer1(q_in)
        q_out2 = self.q_layer2(q_in)
        
        # Concatenate: (Batch, 20)
        q_combined = torch.cat([q_out1, q_out2], dim=1)
        
        # Up-Project and Reshape
        x_out = self.fc_up(q_combined)
        x_out = x_out.view(b, -1, *self.target_spatial_shape)
        
        return x_out

def get_padding(kernel_size: Union[Sequence[int], int], stride: Union[Sequence[int], int]) -> Union[Tuple[int, ...], int]:
    kernel_size_np = np.atleast_1d(kernel_size)
    stride_np = np.atleast_1d(stride)
    padding_np = (kernel_size_np - stride_np + 1) / 2
    if np.min(padding_np) < 0:
        raise AssertionError("padding value should not be negative, please change the kernel size and/or stride.")
    padding = tuple(int(p) for p in padding_np)
    return padding if len(padding) > 1 else padding[0]

def get_output_padding(kernel_size: Union[Sequence[int], int], stride: Union[Sequence[int], int], padding: Union[Sequence[int], int]) -> Union[Tuple[int, ...], int]:
    kernel_size_np = np.atleast_1d(kernel_size)
    stride_np = np.atleast_1d(stride)
    padding_np = np.atleast_1d(padding)
    out_padding_np = 2 * padding_np + stride_np - kernel_size_np
    if np.min(out_padding_np) < 0:
        raise AssertionError("out_padding value should not be negative, please change the kernel size and/or stride.")
    out_padding = tuple(int(p) for p in out_padding_np)
    return out_padding if len(out_padding) > 1 else out_padding[0]

def get_conv_layer(
    spatial_dims: int,
    in_channels: int,
    out_channels: int,
    kernel_size: Union[Sequence[int], int] = 3,
    stride: Union[Sequence[int], int] = 1,
    act: Optional[Union[Tuple, str]] = Act.PRELU,
    norm: Union[Tuple, str] = Norm.INSTANCE,
    dropout: Optional[Union[Tuple, str, float]] = None,
    bias: bool = False,
    conv_only: bool = True,
    is_transposed: bool = False,
):
    padding = get_padding(kernel_size, stride)
    output_padding = None
    if is_transposed:
        output_padding = get_output_padding(kernel_size, stride, padding)
    
    return Convolution(
        spatial_dims,
        in_channels,
        out_channels,
        strides=stride,
        kernel_size=kernel_size,
        act=act,
        norm=norm,
        dropout=dropout,
        bias=bias,
        conv_only=conv_only,
        is_transposed=is_transposed,
        padding=padding,
        output_padding=output_padding,
    )

class UnetBasicBlock(nn.Module):
    def __init__(
        self,
        spatial_dims: int,
        in_channels: int,
        out_channels: int,
        kernel_size: Union[Sequence[int], int],
        stride: Union[Sequence[int], int],
        norm_name: Union[Tuple, str] = ("INSTANCE", {"affine": True}),
        act_name: Union[Tuple, str] = ("leakyrelu", {"inplace": True, "negative_slope": 0.01}),
        dropout: Optional[Union[Tuple, str, float]] = None,
    ):
        super().__init__()
        self.conv1 = get_conv_layer(
            spatial_dims,
            in_channels,
            out_channels,
            kernel_size=kernel_size,
            stride=stride,
            dropout=dropout,
            conv_only=True,
        )

        self.conv2 = get_conv_layer(
            spatial_dims,
            out_channels,
            out_channels,
            kernel_size=kernel_size,
            stride=1,
            dropout=dropout,
            conv_only=True
        )
        self.lrelu = get_act_layer(name=act_name)
        self.norm1 = get_norm_layer(name=norm_name, spatial_dims=spatial_dims, channels=out_channels)
        self.norm2 = get_norm_layer(name=norm_name, spatial_dims=spatial_dims, channels=out_channels)

    def forward(self, inp):
        out = self.conv1(inp)
        out = self.norm1(out)
        out = self.lrelu(out)
        out = self.conv2(out)
        out = self.norm2(out)
        out = self.lrelu(out)
        return out

class UnetUpBlock(nn.Module):
    def __init__(
        self,
        spatial_dims: int,
        in_channels: int,
        out_channels: int,
        kernel_size: Union[Sequence[int], int],
        upsample_kernel_size: Union[Sequence[int], int],
        norm_name: Union[Tuple, str] = ("INSTANCE", {"affine": True}),
        act_name: Union[Tuple, str] = ("leakyrelu", {"inplace": True, "negative_slope": 0.01}),
        dropout: Optional[Union[Tuple, str, float]] = None,
        trans_bias: bool = False,
    ):
        super().__init__()
        upsample_stride = upsample_kernel_size
        
        self.transp_conv = get_conv_layer(
            spatial_dims,
            in_channels,
            out_channels,
            kernel_size=upsample_kernel_size,
            stride=upsample_stride,
            dropout=dropout,
            bias=trans_bias,
            conv_only=True,
            is_transposed=True,
        )
        
        self.conv_block = UnetBasicBlock(
            spatial_dims,
            out_channels + out_channels,
            out_channels,
            kernel_size=kernel_size,
            stride=1,
            dropout=dropout,
            norm_name=norm_name,
            act_name=act_name,
        )

    def forward(self, inp, skip):
        out = self.transp_conv(inp)
        out = torch.cat((out, skip), dim=1)
        out = self.conv_block(out)
        return out

class UnetOutBlock(nn.Module):
    def __init__(
        self, spatial_dims: int, in_channels: int, out_channels: int, dropout: Optional[Union[Tuple, str, float]] = None
    ):
        super().__init__()
        self.conv = get_conv_layer(
            spatial_dims, in_channels, out_channels, kernel_size=1, stride=1, dropout=dropout, bias=True, conv_only=True
        )

    def forward(self, inp):
        return self.conv(inp)

class DynUNet(nn.Module):
    def __init__(
        self,
        spatial_dims: int,
        in_channels: int,
        out_channels: int,
        deep_supervision: bool,
        KD: bool = False
    ):
        super().__init__()
        self.spatial_dims = spatial_dims
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.deep_supervision = deep_supervision
        self.KD_enabled = KD
        
        self.input_conv = UnetBasicBlock( spatial_dims=self.spatial_dims, in_channels=self.in_channels, out_channels=64, kernel_size=3, stride=1)
        self.down1 = UnetBasicBlock( spatial_dims=self.spatial_dims, in_channels=64, out_channels=96, kernel_size=3, stride=2)
        self.down2 = UnetBasicBlock( spatial_dims=self.spatial_dims, in_channels=96, out_channels=128, kernel_size=3, stride=2)
        self.down3 = UnetBasicBlock( spatial_dims=self.spatial_dims, in_channels=128, out_channels=192, kernel_size=3, stride=2)
        self.down4 = UnetBasicBlock( spatial_dims=self.spatial_dims, in_channels=192, out_channels=256, kernel_size=3, stride=2)
        self.down5 = UnetBasicBlock( spatial_dims=self.spatial_dims, in_channels=256, out_channels=384, kernel_size=3, stride=2)
        
        self.quantum_bottleneck = ParallelQuantumBottleneck(
                                     in_channels=384,
                                     out_channels=512,
                                     target_spatial_shape=(2, 2, 2)
                                     )
        
        self.up1 = UnetUpBlock( spatial_dims=self.spatial_dims, in_channels=512, out_channels=384, kernel_size=3, upsample_kernel_size=2)
        self.up2 = UnetUpBlock( spatial_dims=self.spatial_dims, in_channels=384, out_channels=256, kernel_size=3, upsample_kernel_size=2)
        self.up3 = UnetUpBlock( spatial_dims=self.spatial_dims, in_channels=256, out_channels=192, kernel_size=3, upsample_kernel_size=2)
        self.up4 = UnetUpBlock( spatial_dims=self.spatial_dims, in_channels=192, out_channels=128, kernel_size=3, upsample_kernel_size=2)
        self.up5 = UnetUpBlock( spatial_dims=self.spatial_dims, in_channels=128, out_channels=96, kernel_size=3, upsample_kernel_size=2)
        self.up6 = UnetUpBlock( spatial_dims=self.spatial_dims, in_channels=96, out_channels=64, kernel_size=3, upsample_kernel_size=2)
        
        self.out1 = UnetOutBlock( spatial_dims=self.spatial_dims, in_channels=64, out_channels=self.out_channels)
        self.out2 = UnetOutBlock( spatial_dims=self.spatial_dims, in_channels=96, out_channels=self.out_channels)
        self.out3 = UnetOutBlock( spatial_dims=self.spatial_dims, in_channels=128, out_channels=self.out_channels)
        
    def forward( self, input ):
        x0 = self.input_conv( input )
        x1 = self.down1( x0 )
        x2 = self.down2( x1 )
        x3 = self.down3( x2 )
        x4 = self.down4( x3 )
        x5 = self.down5( x4 )
        x6 = self.quantum_bottleneck( x5 )
        
        x7  = self.up1( x6, x5 )
        x8  = self.up2( x7, x4 )
        x9  = self.up3( x8, x3 )
        x10 = self.up4( x9, x2 )
        x11 = self.up5( x10, x1 )
        x12 = self.up6( x11, x0 )
        
        output1 = self.out1( x12 )
        return output1 # Return only the main prediction for inference
