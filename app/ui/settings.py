import json
import os

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
        recents = self.data.get("recent_files", [])
        if file_path in recents:
            recents.remove(file_path)
        recents.insert(0, file_path)
        self.data["recent_files"] = recents[:10]  # Keep last 10
        self.save()

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
