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

from orchestrator_base import AgentOrchestrator, OrchestrationPattern, OrchestrationConfig, AgentConfig, BaseAgent
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
            logger.info("Sistema de Orquestração pronto para uso.")
            
        except RuntimeError as rte: # Captura erros específicos da inicialização de agentes
            logger.critical(f"Erro crítico de runtime ao inicializar o sistema (provavelmente falha na criação de agentes): {rte}", exc_info=True)
            # Dependendo da criticidade, o sistema pode não conseguir operar.
            # Poderia lançar uma exceção específica para ser tratada pela aplicação principal.
            raise RuntimeError(f"Falha crítica na inicialização do OrchestrationSystem: {rte}") from rte
        except Exception as e: # Outros erros inesperados na inicialização
            logger.critical(f"Erro inesperado e crítico ao inicializar o sistema de orquestração: {e}", exc_info=True)
            raise RuntimeError(f"Falha crítica e inesperada na inicialização do OrchestrationSystem: {e}") from e

    async def _create_default_agents(self):
        """Cria agentes padrão do sistema. Levanta RuntimeError se um agente essencial falhar."""
        llm_config = self.config_manager.get_llm_config()
        
        if not llm_config.api_key:
            logger.warning("Chave API do LLM não configurada. Agentes que dependem de LLM podem não funcionar. Continuando com agentes que não dependem de LLM, se houver.")
            # Não retorna aqui, permite que o sistema tente inicializar agentes que não dependem de API key,
            # ou que a ausência da chave seja tratada na inicialização do agente específico.

        agent_types = AgentFactory.get_available_agents() # Usa o método da factory
        
        for agent_type in agent_types:
            try:
                logger.debug(f"Tentando criar e inicializar agente padrão do tipo: {agent_type}")
                agent = AgentFactory.create_agent(agent_type, llm_config)
                await agent.initialize() # Esta chamada pode levantar RuntimeError
                self.agents[agent.name] = agent
                logger.info(f"Agente padrão '{agent.name}' (tipo: {agent_type}) criado e inicializado com sucesso.")
            except ValueError as ve: # Erro da AgentFactory se o tipo for desconhecido
                logger.error(f"Erro de valor ao tentar criar agente do tipo '{agent_type}': {ve}", exc_info=True)
                # Pode ser uma falha de configuração, mas não necessariamente crítica para todos os agentes.
            except RuntimeError as rte: # Erro na inicialização do agente específico (e.g. falha de API)
                logger.error(f"Erro de runtime ao inicializar agente '{agent_type}': {rte}. Este agente pode não estar funcional.", exc_info=True)
                # Decide se a falha de um agente padrão é crítica.
                # Por agora, logamos e continuamos, o agente não estará disponível.
                # Se fosse um agente essencial, poderíamos levantar uma exceção aqui.
            except Exception as e: # Outros erros inesperados
                logger.error(f"Erro inesperado ao criar ou inicializar agente padrão do tipo '{agent_type}': {e}", exc_info=True)

        if not self.agents:
            logger.warning("Nenhum agente padrão foi carregado com sucesso. O sistema pode ter funcionalidade limitada.")

    async def create_orchestrator(self, 
                                name: str, 
                                pattern: str, 
                                agent_names: List[str],
                                max_iterations: Optional[int] = None, # Permitir None para usar default do config
                                timeout: Optional[int] = None) -> str: # Permitir None para usar default do config
        """Cria um novo orquestrador. Levanta ValueError ou RuntimeError em caso de falha."""
        logger.info(f"Tentando criar orquestrador '{name}' com padrão '{pattern}' e agentes: {agent_names}")

        # Valida nome do orquestrador
        if not name or not name.strip():
            logger.error("Falha ao criar orquestrador: Nome não pode ser vazio.")
            raise ValueError("Nome do orquestrador não pode ser vazio.")
        if name in self.orchestrators:
            logger.error(f"Falha ao criar orquestrador: Nome '{name}' já existe.")
            raise ValueError(f"Orquestrador com nome '{name}' já existe.")

        try:
            pattern_enum = OrchestrationPattern(pattern.lower())
        except ValueError: # Se o padrão não for um membro válido do Enum
            logger.error(f"Padrão de orquestração inválido: '{pattern}'. Padrões válidos: {[p.value for p in OrchestrationPattern]}", exc_info=True)
            raise ValueError(f"Padrão de orquestração '{pattern}' é inválido.")

        if not agent_names:
            logger.error(f"Falha ao criar orquestrador '{name}': Lista de agentes não pode ser vazia.")
            raise ValueError("Pelo menos um agente deve ser especificado para o orquestrador.")

        selected_agents_instances: List[BaseAgent] = []
        for agent_name in agent_names:
            agent_instance = self.agents.get(agent_name)
            if not agent_instance:
                logger.error(f"Agente '{agent_name}' não encontrado ou não inicializado no sistema.")
                raise ValueError(f"Agente '{agent_name}' não está disponível no sistema.")
            selected_agents_instances.append(agent_instance)

        # Usa configurações padrão do config_manager se não fornecidas
        orchestration_config_defaults = self.config_manager.get_orchestration_config()
        final_max_iterations = max_iterations if max_iterations is not None else orchestration_config_defaults.get('max_iterations', 10)
        final_timeout = timeout if timeout is not None else orchestration_config_defaults.get('timeout', 300)

        try:
            # Cria configuração para o AgentOrchestrator
            agent_configs_for_orchestrator = [
                AgentConfig(
                    name=agent.name,
                    description=agent.description,
                    capabilities=agent.capabilities,
                    model_config=agent.config.model_config # Usa a model_config original do agente
                ) for agent in selected_agents_instances
            ]
            
            orchestrator_config = OrchestrationConfig(
                pattern=pattern_enum,
                agents=agent_configs_for_orchestrator, # Passa as AgentConfig, não as instâncias
                max_iterations=final_max_iterations,
                timeout=final_timeout
            )
            
            orchestrator = AgentOrchestrator(orchestrator_config)
            
            # Registra as instâncias dos agentes no orquestrador
            for agent_instance in selected_agents_instances:
                await orchestrator.register_agent(agent_instance) # register_agent pode levantar RuntimeError
            
            self.orchestrators[name] = orchestrator
            
            logger.info(f"Orquestrador '{name}' (padrão: {pattern}) criado e configurado com sucesso com {len(selected_agents_instances)} agentes.")
            return name

        except ValueError as ve: # Erros de validação de dados
            logger.error(f"Erro de valor ao criar orquestrador '{name}': {ve}", exc_info=True)
            raise  # Repassa ValueError para ser tratado pela camada de API
        except RuntimeError as rte: # Erros de inicialização de agente dentro do orquestrador
            logger.error(f"Erro de runtime ao configurar agentes para o orquestrador '{name}': {rte}", exc_info=True)
            # Limpar o orquestrador parcialmente criado se ele foi adicionado à lista
            if name in self.orchestrators:
                del self.orchestrators[name]
            raise RuntimeError(f"Falha ao registrar agentes no orquestrador '{name}': {rte}") from rte
        except Exception as e: # Outros erros inesperados
            logger.error(f"Erro inesperado ao criar orquestrador '{name}': {e}", exc_info=True)
            if name in self.orchestrators: # Garante limpeza
                del self.orchestrators[name]
            raise RuntimeError(f"Erro inesperado e não tratado durante a criação do orquestrador '{name}': {e}") from e

    async def execute_orchestration(self, 
                                  orchestrator_name: str, 
                                  task: str, 
                                  context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Executa uma orquestração. Retorna um dicionário com o resultado."""
        logger.info(f"Tentando executar orquestração '{orchestrator_name}' para tarefa: '{task[:100]}...'")

        if not orchestrator_name or orchestrator_name not in self.orchestrators:
            logger.error(f"Falha na execução: Orquestrador '{orchestrator_name}' não encontrado.")
            # Retorna um dict de erro padronizado em vez de levantar exceção diretamente aqui,
            # para que a API possa controlar melhor a resposta HTTP.
            return {
                "success": False,
                "error": f"Orquestrador '{orchestrator_name}' não encontrado.",
                "execution_time": 0,
                "orchestrator_name": orchestrator_name,
                "timestamp": datetime.now().isoformat()
            }
        
        orchestrator = self.orchestrators[orchestrator_name]
        start_time = time.time()
        
        try:
            # A validação de task e context pode ser adicionada aqui se necessário
            if not task or not task.strip():
                logger.warning(f"Tarefa para orquestrador '{orchestrator_name}' está vazia.")
                # Pode-se decidir retornar um erro ou prosseguir
            
            result = await orchestrator.orchestrate(task, context) # Este método já trata seus próprios erros e retorna um dict
            
            execution_time = time.time() - start_time
            result["execution_time"] = execution_time # Adiciona ao resultado do orchestrate
            result["orchestrator_name"] = orchestrator_name
            result["timestamp"] = datetime.now().isoformat()

            # Registra métricas com base no 'success' retornado pelo orchestrate
            agents_used = list(orchestrator.agents.keys()) # orchestrator.agents contém instâncias
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
            
            if result.get("success"):
                logger.info(f"Orquestração '{orchestrator_name}' (padrão: {orchestrator.pattern.value}) concluída com sucesso em {execution_time:.2f}s.")
            else:
                logger.warning(f"Orquestração '{orchestrator_name}' (padrão: {orchestrator.pattern.value}) concluída com falha em {execution_time:.2f}s. Erro: {result.get('error', 'Não especificado')}")
            
            return result
            
        except Exception as e: # Captura erros inesperados que não foram tratados pelo orchestrator.orchestrate()
            execution_time = time.time() - start_time
            logger.critical(f"Erro crítico e inesperado durante a execução da orquestração '{orchestrator_name}': {e}", exc_info=True)
            
            # Registra falha nas métricas
            if orchestrator_name in self.orchestrators: # Verifica se o orquestrador ainda existe
                pattern_value = self.orchestrators[orchestrator_name].pattern.value
                agents_in_orchestrator = list(self.orchestrators[orchestrator_name].agents.keys())
            else: # Orquestrador pode ter sido removido ou nunca existiu
                pattern_value = "unknown"
                agents_in_orchestrator = []

            self.metrics_collector.record_orchestration(
                pattern=pattern_value,
                success=False,
                execution_time=execution_time,
                agents_used=agents_in_orchestrator
            )
            
            return {
                "success": False,
                "error": f"Ocorreu um erro crítico e inesperado no servidor durante a orquestração: {e}",
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
        if not name or not name.strip():
            logger.error("Falha ao definir workflow: Nome do workflow não pode ser vazio.")
            raise ValueError("Nome do workflow não pode ser vazio.")
        if name in self.workflows:
            logger.error(f"Falha ao definir workflow: Nome '{name}' já existe.")
            raise ValueError(f"Workflow com nome '{name}' já existe.")
        if not steps:
            logger.error(f"Falha ao definir workflow '{name}': Lista de etapas (steps) não pode ser vazia.")
            raise ValueError("Workflow deve ter pelo menos uma etapa.")

        for i, step in enumerate(steps):
            if "orchestrator" not in step or not step["orchestrator"]:
                logger.error(f"Falha ao definir workflow '{name}': Etapa {i+1} não possui nome de orquestrador.")
                raise ValueError(f"Etapa {i+1} do workflow '{name}' deve especificar um orquestrador.")
            # Validação adicional: verificar se o orquestrador da etapa existe no sistema?
            # Isso pode ser feito aqui ou no momento da execução do workflow.
            # Por ora, deixamos para a execução, pois orquestradores podem ser criados dinamicamente.

        self.workflows[name] = {
            "name": name,
            "description": description or f"Workflow '{name}'", # Default description
            "steps": steps,
            "created_at": datetime.now().isoformat()
        }
        
        logger.info(f"Workflow '{name}' definido com {len(steps)} etapas.")
    
    async def execute_workflow(self, 
                             workflow_name: str, 
                             initial_input: str, 
                             context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Executa um workflow completo. Retorna um dicionário com o resultado."""
        logger.info(f"Tentando executar workflow '{workflow_name}' com input inicial: '{initial_input[:100]}...'")

        if workflow_name not in self.workflows:
            logger.error(f"Falha na execução do workflow: Workflow '{workflow_name}' não encontrado.")
            return {
                "success": False,
                "workflow_name": workflow_name,
                "error": f"Workflow '{workflow_name}' não encontrado.",
                "results": [],
                "timestamp": datetime.now().isoformat()
            }
        
        workflow_definition = self.workflows[workflow_name]
        workflow_results = []
        current_task_input = initial_input
        
        if context is None:
            context = {}
        
        overall_success = True # Assume sucesso até que uma etapa falhe

        try:
            for i, step_config in enumerate(workflow_definition["steps"]):
                step_name = step_config.get("name", f"Etapa {i+1}")
                orchestrator_name_for_step = step_config["orchestrator"]
                
                logger.info(f"Workflow '{workflow_name}': Executando etapa '{step_name}' usando orquestrador '{orchestrator_name_for_step}'.")
                
                # Executa a etapa da orquestração
                # execute_orchestration já trata seus erros e retorna um dict
                step_execution_result = await self.system.execute_orchestration(
                    orchestrator_name=orchestrator_name_for_step,
                    task=current_task_input,
                    context=context # O contexto pode ser modificado entre etapas se necessário
                )
                
                workflow_results.append({
                    "step_name": step_name,
                    "orchestrator": orchestrator_name_for_step,
                    "result": step_execution_result # Armazena o dict completo do resultado da etapa
                })
                
                if not step_execution_result.get("success"):
                    logger.warning(f"Workflow '{workflow_name}': Etapa '{step_name}' falhou. Erro: {step_execution_result.get('error', 'Não especificado')}. Interrompendo workflow.")
                    overall_success = False
                    break # Interrompe o workflow se uma etapa falhar

                # Prepara a entrada para a próxima etapa
                # A lógica para determinar o input da próxima etapa pode ser complexa.
                # Por padrão, usa-se o 'final_output' se existir.
                if "final_output" in step_execution_result and step_execution_result["final_output"] is not None:
                    current_task_input = step_execution_result["final_output"]
                elif "results" in step_execution_result and isinstance(step_execution_result["results"], list) and step_execution_result["results"]:
                    # Para orquestração concorrente, pode-se pegar o output do primeiro resultado bem-sucedido,
                    # ou concatenar, ou uma lógica customizada.
                    # Aqui, um exemplo simples: Pega o output do primeiro resultado que tenha 'output'.
                    first_successful_output = next((res.get("output") for res in step_execution_result["results"] if res.get("success") and "output" in res), None)
                    if first_successful_output is not None:
                        current_task_input = first_successful_output
                    else:
                        logger.warning(f"Workflow '{workflow_name}', Etapa '{step_name}': Não foi possível determinar a próxima entrada a partir do resultado. Usando a entrada anterior: '{current_task_input[:50]}...'")
                        # Mantém current_task_input como estava, ou poderia ser um erro.
                else:
                    logger.warning(f"Workflow '{workflow_name}', Etapa '{step_name}': Resultado da etapa não continha 'final_output' ou 'results' esperados para determinar a próxima entrada. Usando a entrada anterior: '{current_task_input[:50]}...'")

            final_message = "Workflow concluído com sucesso." if overall_success else "Workflow concluído com falhas."
            logger.info(f"Workflow '{workflow_name}': {final_message}")
            
            return {
                "success": overall_success,
                "workflow_name": workflow_name,
                "results": workflow_results,
                "final_output": current_task_input if overall_success else None, # Output final apenas se tudo ocorreu bem
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e: # Captura erros inesperados na lógica do workflow em si
            logger.critical(f"Erro crítico e inesperado durante a execução do workflow '{workflow_name}': {e}", exc_info=True)
            return {
                "success": False,
                "workflow_name": workflow_name,
                "error": f"Ocorreu um erro crítico no servidor durante a execução do workflow: {e}",
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

