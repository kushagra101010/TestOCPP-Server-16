import configparser
import os
from typing import Dict, Any

class Config:
    def __init__(self, config_file: str = "config.ini"):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.load_config()
    
    def load_config(self):
        """Load configuration from file"""
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
        else:
            # Create default config if file doesn't exist
            self._create_default_config()
    
    def _create_default_config(self):
        """Create default configuration"""
        self.config['SERVER'] = {
            'host': '0.0.0.0',
            'port': '8000',
            'debug': 'false',
            'reload': 'false'
        }
        
        self.config['LOGGING'] = {
            'log_level': 'INFO',
            'log_to_file': 'true',
            'log_file': 'logs/ocpp_server.log',
            'max_log_size_mb': '10',
            'backup_count': '5'
        }
        
        self.config['FEATURES'] = {
            'enable_demo_charger': 'true',
            'enable_api_docs': 'true',
            'enable_metrics': 'false'
        }
        
        self.config['UI_FEATURES'] = {
            'show_jio_bp_data_transfer': 'true',
            'show_msil_data_transfer': 'false',
            'show_cz_data_transfer': 'true'
        }
        
        self.config['NETWORK'] = {
            'websocket_ping_interval': '30',
            'websocket_ping_timeout': '10',
            'max_message_size': '65536'
        }
        
        # Save default config
        with open(self.config_file, 'w') as f:
            self.config.write(f)
    
    def get(self, section: str, key: str, fallback: str = None) -> str:
        """Get configuration value"""
        return self.config.get(section, key, fallback=fallback)
    
    def getboolean(self, section: str, key: str, fallback: bool = False) -> bool:
        """Get boolean configuration value"""
        return self.config.getboolean(section, key, fallback=fallback)
    
    def getint(self, section: str, key: str, fallback: int = 0) -> int:
        """Get integer configuration value"""
        return self.config.getint(section, key, fallback=fallback)
    
    def get_ui_features(self) -> Dict[str, bool]:
        """Get UI feature toggles"""
        ui_features = {}
        if 'UI_FEATURES' in self.config:
            for key in self.config['UI_FEATURES']:
                ui_features[key] = self.getboolean('UI_FEATURES', key, fallback=True)
        return ui_features
    
    def get_server_config(self) -> Dict[str, Any]:
        """Get server configuration"""
        return {
            'host': self.get('SERVER', 'host', '0.0.0.0'),
            'port': self.getint('SERVER', 'port', 8000),
            'debug': self.getboolean('SERVER', 'debug', False),
            'reload': self.getboolean('SERVER', 'reload', False)
        }

# Global config instance
config = Config() 