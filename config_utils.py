"""
Configurações e utilitários para o Orquestrador de Agentes
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuração para modelos de linguagem"""
    provider: str  # "openai", "azure", "local", etc.
    model_name: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    api_version: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1000
    timeout: int = 30


@dataclass
class PluginConfig:
    """Configuração para plugins"""
    name: str
    type: str  # "function", "semantic", "native"
    description: str
    parameters: Dict[str, Any] = None


class ConfigManager:
    """Gerenciador de configurações"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Carrega configurações do arquivo"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    logger.info(f"Configuração carregada com sucesso de {self.config_file}")
                    return config_data
            except FileNotFoundError:
                logger.error(f"Arquivo de configuração {self.config_file} não encontrado. Usando configuração padrão.")
            except json.JSONDecodeError as e:
                logger.error(f"Erro ao decodificar JSON do arquivo {self.config_file}: {e}. Usando configuração padrão.")
            except Exception as e:
                logger.error(f"Erro inesperado ao carregar {self.config_file}: {e}. Usando configuração padrão.")
        else:
            logger.info(f"Arquivo de configuração {self.config_file} não encontrado. Usando configuração padrão.")
        return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Retorna configuração padrão"""
        return {
            "llm": {
                "provider": "openai",
                "model_name": "gpt-3.5-turbo",
                "api_key": os.getenv("OPENAI_API_KEY"),
                "temperature": 0.7,
                "max_tokens": 1000,
                "timeout": 30
            },
            "orchestration": {
                "max_iterations": 10,
                "timeout": 300,
                "default_pattern": "sequential"
            },
            "agents": {
                "max_concurrent": 5,
                "retry_attempts": 3,
                "retry_delay": 1
            },
            "logging": {
                "level": "INFO",
                "file": "orchestrator.log"
            }
        }
    
    def save_config(self):
        """Salva configurações no arquivo"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logger.info(f"Configuração salva com sucesso em {self.config_file}")
        except IOError as e:
            logger.error(f"Erro de I/O ao salvar configuração em {self.config_file}: {e}")
        except Exception as e:
            logger.error(f"Erro inesperado ao salvar configuração em {self.config_file}: {e}")

    def get_llm_config(self) -> LLMConfig:
        """Retorna configuração do LLM"""
        llm_config = self.config.get("llm", {})
        return LLMConfig(**llm_config)
    
    def get_orchestration_config(self) -> Dict[str, Any]:
        """Retorna configuração de orquestração"""
        return self.config.get("orchestration", {})
    
    def get_agents_config(self) -> Dict[str, Any]:
        """Retorna configuração de agentes"""
        return self.config.get("agents", {})
    
    def update_config(self, section: str, updates: Dict[str, Any]):
        """Atualiza uma seção da configuração"""
        if section not in self.config:
            self.config[section] = {}
        self.config[section].update(updates)
        self.save_config()


class ValidationUtils:
    """Utilitários para validação"""
    
    @staticmethod
    def validate_agent_config(config: Dict[str, Any]) -> bool:
        """Valida configuração de agente"""
        required_fields = ["name", "description", "capabilities"]
        return all(field in config for field in required_fields)
    
    @staticmethod
    def validate_llm_config(config: LLMConfig) -> bool:
        """Valida configuração do LLM"""
        if not config.provider or not config.model_name:
            return False
        
        if config.provider == "openai" and not config.api_key:
            return False
        
        return True
    
    @staticmethod
    def validate_orchestration_pattern(pattern: str) -> bool:
        """Valida padrão de orquestração"""
        valid_patterns = ["sequential", "concurrent", "group_chat", "handoff"]
        return pattern.lower() in valid_patterns


class LoggingUtils:
    """Utilitários para logging"""
    
    @staticmethod
    def setup_logging(config: Dict[str, Any]):
        """Configura logging baseado na configuração"""
        import logging
        # Removida a importação de logging, pois já está no topo do arquivo.
        
        log_level_str = config.get("level", "INFO").upper()
        log_level = getattr(logging, log_level_str, logging.INFO)
        log_file = config.get("file", "orchestrator.log")

        # Remove handlers existentes para evitar duplicação se a função for chamada múltiplas vezes
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        handlers = [logging.StreamHandler()]
        if log_file:
            try:
                file_handler = logging.FileHandler(log_file, encoding='utf-8')
                handlers.append(file_handler)
            except Exception as e:
                logging.error(f"Não foi possível criar o handler de arquivo de log {log_file}: {e}. Logando apenas no console.")

        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=handlers
        )
        logger.info(f"Logging configurado. Nível: {log_level_str}, Arquivo: {log_file if log_file else 'N/A'}")


class MetricsCollector:
    """Coletor de métricas"""
    
    def __init__(self):
        self.metrics = {
            "orchestrations_count": 0,
            "successful_orchestrations": 0,
            "failed_orchestrations": 0,
            "average_execution_time": 0,
            "agents_usage": {},
            "patterns_usage": {}
        }
    
    def record_orchestration(self, pattern: str, success: bool, execution_time: float, agents_used: list):
        """Registra uma orquestração"""
        self.metrics["orchestrations_count"] += 1
        
        if success:
            self.metrics["successful_orchestrations"] += 1
        else:
            self.metrics["failed_orchestrations"] += 1
        
        # Atualiza tempo médio de execução
        total_time = self.metrics["average_execution_time"] * (self.metrics["orchestrations_count"] - 1)
        self.metrics["average_execution_time"] = (total_time + execution_time) / self.metrics["orchestrations_count"]
        
        # Registra uso de padrões
        if pattern not in self.metrics["patterns_usage"]:
            self.metrics["patterns_usage"][pattern] = 0
        self.metrics["patterns_usage"][pattern] += 1
        
        # Registra uso de agentes
        for agent in agents_used:
            if agent not in self.metrics["agents_usage"]:
                self.metrics["agents_usage"][agent] = 0
            self.metrics["agents_usage"][agent] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Retorna métricas coletadas"""
        return self.metrics.copy()
    
    def reset_metrics(self):
        """Reseta métricas"""
        self.metrics = {
            "orchestrations_count": 0,
            "successful_orchestrations": 0,
            "failed_orchestrations": 0,
            "average_execution_time": 0,
            "agents_usage": {},
            "patterns_usage": {}
        }


if __name__ == "__main__":
    # Teste das configurações
    config_manager = ConfigManager()
    print("Configuração carregada:")
    print(json.dumps(config_manager.config, indent=2, ensure_ascii=False))
    
    # Teste das métricas
    metrics = MetricsCollector()
    metrics.record_orchestration("sequential", True, 2.5, ["agent1", "agent2"])
    print("\nMétricas:")
    print(json.dumps(metrics.get_metrics(), indent=2, ensure_ascii=False))

