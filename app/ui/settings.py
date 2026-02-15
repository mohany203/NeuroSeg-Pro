import json
import os
import sys

SETTINGS_FILE = "settings.json"

DEFAULT_SETTINGS = {
    "theme": "Dark",
    "font_size": 14,  # Reset to standard size

    "visual_quality": "High",
    "default_opacity": 0.6,
    "show_grid": True,
    "recent_files": [],
    "models": [
        {
            "id": "default", 
            "name": "Default (Teacher Model)", 
            "path": "model_output/Teacher_model_after_epoch_26_trainLoss_1.3478_valLoss_0.6119.pth"
        }
    ],
    "active_model_id": "default",
    "ask_model_on_run": False
}

class Settings:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Settings, cls).__new__(cls)
            cls._instance.load()
        return cls._instance

    def load(self):
        self.data = DEFAULT_SETTINGS.copy()
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    loaded = json.load(f)
                    self.data.update(loaded)
            except Exception as e:
                print(f"Error loading settings: {e}")
        
        # Always scan for new models in 'models' folder
        self.scan_for_models()

    def scan_for_models(self):
        """Scans the 'models' directory next to the executable/script for .pth files."""
        # Determine base path
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.abspath(".")
            
        models_dir = os.path.join(base_dir, "models")
        if not os.path.exists(models_dir):
            try:
                os.makedirs(models_dir)
            except OSError:
                pass # Might be read-only
                
        if os.path.exists(models_dir):
            for f in os.listdir(models_dir):
                if f.endswith(".pth"):
                    full_path = os.path.join(models_dir, f)
                    # Check if already registered
                    existing = [m for m in self.data.get("models", []) if os.path.normpath(m["path"]) == os.path.normpath(full_path)]
                    if not existing:
                        self.add_model(name=f, path=full_path)

    def save(self):
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def get(self, key):
        return self.data.get(key, DEFAULT_SETTINGS.get(key))

    def set(self, key, value):
        self.data[key] = value
        self.save()

    def add_recent(self, file_path):
        from datetime import datetime
        recents = self.data.get("recent_files", [])
        
        # Remove existing if present (handle both string and dict)
        recents = [r for r in recents if (isinstance(r, dict) and r['path'] != file_path) or (isinstance(r, str) and r != file_path)]
        
        # Add new entry
        entry = {
            "path": file_path,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        recents.insert(0, entry)
        self.data["recent_files"] = recents[:10]  # Keep last 10
        self.save()

    def remove_recent(self, file_path):
        recents = self.data.get("recent_files", [])
        # Filter out the specific path
        new_recents = [r for r in recents if (isinstance(r, dict) and r['path'] != file_path) or (isinstance(r, str) and r != file_path)]
        
        if len(new_recents) != len(recents):
            self.data["recent_files"] = new_recents
            self.save()
            return True
        return False

    def get_recent_files(self):
        """Returns recent files, normalizing them to dicts."""
        raw = self.data.get("recent_files", [])
        normalized = []
        for r in raw:
            if isinstance(r, str):
                normalized.append({"path": r, "timestamp": "Unknown"})
            elif isinstance(r, dict):
                normalized.append(r)
        return normalized

    def add_model(self, name, path):
        """Adds a new model to the registry."""
        import uuid
        model_id = str(uuid.uuid4())
        new_model = {"id": model_id, "name": name, "path": path}
        
        models = self.data.get("models", [])
        models.append(new_model)
        self.data["models"] = models
        self.save()
        return new_model

    def remove_model(self, model_id):
        """Removes a model by ID."""
        models = self.data.get("models", [])
        models = [m for m in models if m["id"] != model_id]
        self.data["models"] = models
        
        # Reset active if deleted
        if self.data.get("active_model_id") == model_id:
            if models:
                self.data["active_model_id"] = models[0]["id"]
            else:
                self.data["active_model_id"] = None
            
        self.save()
        return True

    def get_models(self):
        return self.data.get("models", [])

    def get_active_model(self):
        models = self.get_models()
        active_id = self.data.get("active_model_id")
        
        # Try to find active
        for m in models:
            if m["id"] == active_id:
                return m
        
        # Fallback to first if available
        if models:
            return models[0]
            
        return None

    def set_active_model(self, model_id):
        """Sets the default/active model."""
        self.data["active_model_id"] = model_id
        self.save()
