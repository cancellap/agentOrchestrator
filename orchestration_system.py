"""
Sistema de Orquestração Principal
Integra todos os componentes e fornece interface para uso
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import json

from orchestrator_base import AgentOrchestrator, OrchestrationPattern, OrchestrationConfig, AgentConfig
from specialized_agents import AgentFactory, SemanticKernelAgent
from config_utils import ConfigManager, MetricsCollector, LoggingUtils

logger = logging.getLogger(__name__)


class OrchestrationSystem:
    """Sistema principal de orquestração de agentes"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_manager = ConfigManager(config_file)
        self.metrics_collector = MetricsCollector()
        self.orchestrators: Dict[str, AgentOrchestrator] = {}
        self.agents: Dict[str, SemanticKernelAgent] = {}
        
        # Configura logging
        logging_config = self.config_manager.config.get("logging", {})
        LoggingUtils.setup_logging(logging_config)
        
        logger.info("Sistema de Orquestração inicializado")
    
    async def initialize(self):
        """Inicializa o sistema"""
        try:
            # Cria agentes padrão
            await self._create_default_agents()
            logger.info("Sistema de Orquestração pronto para uso")
            
        except Exception as e:
            logger.error(f"Erro ao inicializar sistema: {str(e)}")
            raise
    
    async def _create_default_agents(self):
        """Cria agentes padrão do sistema"""
        llm_config = self.config_manager.get_llm_config()
        
        # Verifica se a configuração do LLM é válida
        if not llm_config.api_key:
            logger.warning("Chave API não configurada. Alguns recursos podem não funcionar.")
            return
        
        # Cria agentes especializados
        agent_types = ["analyst", "writer", "planner", "reviewer"]
        
        for agent_type in agent_types:
            try:
                agent = AgentFactory.create_agent(agent_type, llm_config)
                await agent.initialize()
                self.agents[agent.name] = agent
                logger.info(f"Agente {agent.name} criado e inicializado")
                
            except Exception as e:
                logger.error(f"Erro ao criar agente {agent_type}: {str(e)}")
    
    async def create_orchestrator(self, 
                                name: str, 
                                pattern: str, 
                                agent_names: List[str],
                                max_iterations: int = 10,
                                timeout: int = 300) -> str:
        """Cria um novo orquestrador"""
        try:
            # Valida padrão
            pattern_enum = OrchestrationPattern(pattern.lower())
            
            # Valida agentes
            selected_agents = []
            for agent_name in agent_names:
                if agent_name not in self.agents:
                    raise ValueError(f"Agente não encontrado: {agent_name}")
                selected_agents.append(self.agents[agent_name])
            
            # Cria configuração
            agent_configs = [
                AgentConfig(
                    name=agent.name,
                    description=agent.description,
                    capabilities=agent.capabilities,
                    model_config={}
                ) for agent in selected_agents
            ]
            
            config = OrchestrationConfig(
                pattern=pattern_enum,
                agents=agent_configs,
                max_iterations=max_iterations,
                timeout=timeout
            )
            
            # Cria orquestrador
            orchestrator = AgentOrchestrator(config)
            
            # Registra agentes
            for agent in selected_agents:
                await orchestrator.register_agent(agent)
            
            # Armazena orquestrador
            self.orchestrators[name] = orchestrator
            
            logger.info(f"Orquestrador '{name}' criado com padrão {pattern}")
            return name
            
        except Exception as e:
            logger.error(f"Erro ao criar orquestrador: {str(e)}")
            raise
    
    async def execute_orchestration(self, 
                                  orchestrator_name: str, 
                                  task: str, 
                                  context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Executa uma orquestração"""
        if orchestrator_name not in self.orchestrators:
            raise ValueError(f"Orquestrador não encontrado: {orchestrator_name}")
        
        orchestrator = self.orchestrators[orchestrator_name]
        
        start_time = time.time()
        
        try:
            logger.info(f"Executando orquestração '{orchestrator_name}' com tarefa: {task}")
            
            # Executa orquestração
            result = await orchestrator.orchestrate(task, context)
            
            execution_time = time.time() - start_time
            
            # Registra métricas
            agents_used = list(orchestrator.agents.keys())
            self.metrics_collector.record_orchestration(
                pattern=orchestrator.pattern.value,
                success=result.get("success", False),
                execution_time=execution_time,
                agents_used=agents_used
            )
            
            # Adiciona informações de execução
            result["execution_time"] = execution_time
            result["orchestrator_name"] = orchestrator_name
            result["timestamp"] = datetime.now().isoformat()
            
            logger.info(f"Orquestração '{orchestrator_name}' concluída em {execution_time:.2f}s")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Registra erro nas métricas
            agents_used = list(orchestrator.agents.keys())
            self.metrics_collector.record_orchestration(
                pattern=orchestrator.pattern.value,
                success=False,
                execution_time=execution_time,
                agents_used=agents_used
            )
            
            logger.error(f"Erro na orquestração '{orchestrator_name}': {str(e)}")
            
            return {
                "success": False,
                "error": str(e),
                "execution_time": execution_time,
                "orchestrator_name": orchestrator_name,
                "timestamp": datetime.now().isoformat()
            }
    
    def get_available_agents(self) -> List[Dict[str, Any]]:
        """Retorna lista de agentes disponíveis"""
        return [
            {
                "name": agent.name,
                "description": agent.description,
                "capabilities": agent.capabilities
            }
            for agent in self.agents.values()
        ]
    
    def get_orchestrators(self) -> List[Dict[str, Any]]:
        """Retorna lista de orquestradores"""
        return [
            {
                "name": name,
                "pattern": orchestrator.pattern.value,
                "agents": list(orchestrator.agents.keys()),
                "status": orchestrator.get_status()
            }
            for name, orchestrator in self.orchestrators.items()
        ]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Retorna métricas do sistema"""
        return self.metrics_collector.get_metrics()
    
    def get_system_status(self) -> Dict[str, Any]:
        """Retorna status do sistema"""
        return {
            "agents_count": len(self.agents),
            "orchestrators_count": len(self.orchestrators),
            "available_agents": [agent.name for agent in self.agents.values()],
            "orchestrators": list(self.orchestrators.keys()),
            "metrics": self.get_metrics(),
            "timestamp": datetime.now().isoformat()
        }
    
    async def shutdown(self):
        """Finaliza o sistema"""
        logger.info("Finalizando Sistema de Orquestração")
        # Aqui você pode adicionar lógica de limpeza se necessário


class OrchestrationWorkflow:
    """Classe para definir e executar workflows complexos"""
    
    def __init__(self, system: OrchestrationSystem):
        self.system = system
        self.workflows: Dict[str, Dict[str, Any]] = {}
    
    def define_workflow(self, 
                       name: str, 
                       steps: List[Dict[str, Any]], 
                       description: str = ""):
        """Define um workflow de múltiplas etapas"""
        self.workflows[name] = {
            "name": name,
            "description": description,
            "steps": steps,
            "created_at": datetime.now().isoformat()
        }
        
        logger.info(f"Workflow '{name}' definido com {len(steps)} etapas")
    
    async def execute_workflow(self, 
                             workflow_name: str, 
                             initial_input: str, 
                             context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Executa um workflow completo"""
        if workflow_name not in self.workflows:
            raise ValueError(f"Workflow não encontrado: {workflow_name}")
        
        workflow = self.workflows[workflow_name]
        results = []
        current_input = initial_input
        
        if context is None:
            context = {}
        
        logger.info(f"Executando workflow '{workflow_name}'")
        
        try:
            for i, step in enumerate(workflow["steps"]):
                step_name = step.get("name", f"Etapa {i+1}")
                orchestrator_name = step["orchestrator"]
                
                logger.info(f"Executando {step_name}")
                
                # Executa etapa
                step_result = await self.system.execute_orchestration(
                    orchestrator_name=orchestrator_name,
                    task=current_input,
                    context=context
                )
                
                # Armazena resultado
                results.append({
                    "step_name": step_name,
                    "orchestrator": orchestrator_name,
                    "result": step_result
                })
                
                # Prepara entrada para próxima etapa
                if step_result.get("success"):
                    if "final_output" in step_result:
                        current_input = step_result["final_output"]
                    elif "results" in step_result and step_result["results"]:
                        # Para orquestração concorrente, pega o primeiro resultado
                        current_input = step_result["results"][0].get("output", current_input)
                else:
                    # Se uma etapa falhar, interrompe o workflow
                    break
            
            return {
                "success": True,
                "workflow_name": workflow_name,
                "results": results,
                "final_output": current_input,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro no workflow '{workflow_name}': {str(e)}")
            return {
                "success": False,
                "workflow_name": workflow_name,
                "error": str(e),
                "results": results,
                "timestamp": datetime.now().isoformat()
            }
    
    def get_workflows(self) -> List[Dict[str, Any]]:
        """Retorna lista de workflows definidos"""
        return list(self.workflows.values())


if __name__ == "__main__":
    async def main():
        # Exemplo de uso do sistema
        system = OrchestrationSystem()
        
        try:
            await system.initialize()
            
            print("=== Sistema de Orquestração ===")
            print(f"Agentes disponíveis: {len(system.get_available_agents())}")
            
            for agent in system.get_available_agents():
                print(f"- {agent['name']}: {agent['description']}")
            
            # Exemplo de criação de orquestrador
            if system.agents:
                agent_names = list(system.agents.keys())[:2]  # Pega os primeiros 2 agentes
                
                orchestrator_name = await system.create_orchestrator(
                    name="exemplo_sequencial",
                    pattern="sequential",
                    agent_names=agent_names
                )
                
                print(f"\nOrquestrador '{orchestrator_name}' criado com sucesso!")
                print("Sistema pronto para uso.")
            else:
                print("Nenhum agente disponível (configure OPENAI_API_KEY)")
            
        except Exception as e:
            print(f"Erro: {str(e)}")
        
        finally:
            await system.shutdown()
    
    # Executa exemplo
    asyncio.run(main())

