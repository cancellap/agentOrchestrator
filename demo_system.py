"""
Exemplo de uso do Sistema de Orquestração de Agentes
Demonstra como usar o sistema sem necessidade de API key
"""

import asyncio
import json
import os
import sys

# Adiciona o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from orchestration_system import OrchestrationSystem, OrchestrationWorkflow
from config_utils import ConfigManager


class MockAgent:
    """Agente simulado para demonstração"""
    
    def __init__(self, name, description, capabilities):
        self.name = name
        self.description = description
        self.capabilities = capabilities
    
    async def initialize(self):
        """Inicializa o agente simulado"""
        print(f"Agente {self.name} inicializado (simulado)")
    
    async def process(self, input_data, context=None):
        """Processa entrada de forma simulada"""
        # Simula processamento baseado no tipo de agente
        if "analista" in self.name.lower():
            return f"Análise de '{input_data}': Identificados padrões importantes e tendências relevantes."
        elif "redator" in self.name.lower():
            return f"Conteúdo criado para '{input_data}': Texto envolvente e bem estruturado produzido."
        elif "planejador" in self.name.lower():
            return f"Plano para '{input_data}': Estratégia detalhada com etapas e cronograma definidos."
        elif "revisor" in self.name.lower():
            return f"Revisão de '{input_data}': Qualidade verificada, melhorias sugeridas."
        else:
            return f"Processamento de '{input_data}' concluído pelo agente {self.name}."


async def create_demo_system():
    """Cria sistema de demonstração com agentes simulados"""
    print("🎭 Criando Sistema de Demonstração")
    print("=" * 50)
    
    # Cria sistema
    system = OrchestrationSystem()
    
    # Cria agentes simulados
    mock_agents = [
        MockAgent("Analista", "Especialista em análise de dados e insights", 
                 ["análise", "padrões", "relatórios"]),
        MockAgent("Redator", "Especialista em criação de conteúdo", 
                 ["redação", "conteúdo", "comunicação"]),
        MockAgent("Planejador", "Especialista em estratégia e planejamento", 
                 ["planejamento", "estratégia", "organização"]),
        MockAgent("Revisor", "Especialista em qualidade e revisão", 
                 ["revisão", "qualidade", "validação"])
    ]
    
    # Substitui os agentes do sistema pelos simulados
    system.agents = {agent.name: agent for agent in mock_agents}
    
    # Inicializa agentes simulados
    for agent in mock_agents:
        await agent.initialize()
    
    print(f"✓ Sistema criado com {len(mock_agents)} agentes simulados")
    
    return system


async def demo_sequential_orchestration(system):
    """Demonstra orquestração sequencial"""
    print("\n🔄 Demonstração: Orquestração Sequencial")
    print("-" * 40)
    
    # Cria orquestrador sequencial
    orchestrator_name = await system.create_orchestrator(
        name="demo_sequencial",
        pattern="sequential",
        agent_names=["Analista", "Redator"]
    )
    
    print(f"✓ Orquestrador '{orchestrator_name}' criado")
    
    # Executa orquestração
    task = "Criar um relatório sobre tendências de IA em 2025"
    
    print(f"📝 Executando tarefa: {task}")
    
    result = await system.execute_orchestration(
        orchestrator_name=orchestrator_name,
        task=task,
        context={"formato": "relatório executivo"}
    )
    
    print(f"✓ Orquestração concluída em {result.get('execution_time', 0):.2f}s")
    
    if result.get('success'):
        print("📊 Resultados:")
        for i, step_result in enumerate(result.get('results', []), 1):
            print(f"  {i}. {step_result['agent']}: {step_result['output']}")
        
        print(f"\n🎯 Resultado Final: {result.get('final_output', 'N/A')}")
    else:
        print(f"❌ Erro: {result.get('error', 'Desconhecido')}")


async def demo_concurrent_orchestration(system):
    """Demonstra orquestração concorrente"""
    print("\n⚡ Demonstração: Orquestração Concorrente")
    print("-" * 40)
    
    # Cria orquestrador concorrente
    orchestrator_name = await system.create_orchestrator(
        name="demo_concorrente",
        pattern="concurrent",
        agent_names=["Planejador", "Revisor"]
    )
    
    print(f"✓ Orquestrador '{orchestrator_name}' criado")
    
    # Executa orquestração
    task = "Desenvolver estratégia de marketing para produto inovador"
    
    print(f"📝 Executando tarefa: {task}")
    
    result = await system.execute_orchestration(
        orchestrator_name=orchestrator_name,
        task=task,
        context={"público": "empresas", "orçamento": "médio"}
    )
    
    print(f"✓ Orquestração concluída em {result.get('execution_time', 0):.2f}s")
    
    if result.get('success'):
        print("📊 Resultados (processamento paralelo):")
        for i, step_result in enumerate(result.get('results', []), 1):
            print(f"  {i}. {step_result['agent']}: {step_result['output']}")
    else:
        print(f"❌ Erro: {result.get('error', 'Desconhecido')}")


async def demo_workflow(system):
    """Demonstra workflow complexo"""
    print("\n🔗 Demonstração: Workflow Complexo")
    print("-" * 40)
    
    # Cria workflow manager
    workflow_manager = OrchestrationWorkflow(system)
    
    # Define workflow
    workflow_steps = [
        {
            "name": "Análise de Mercado",
            "orchestrator": "demo_sequencial"
        },
        {
            "name": "Estratégia Paralela",
            "orchestrator": "demo_concorrente"
        }
    ]
    
    workflow_manager.define_workflow(
        name="workflow_completo",
        steps=workflow_steps,
        description="Workflow de análise e estratégia"
    )
    
    print("✓ Workflow definido com 2 etapas")
    
    # Executa workflow
    task = "Lançar novo produto de tecnologia"
    
    print(f"📝 Executando workflow: {task}")
    
    result = await workflow_manager.execute_workflow(
        workflow_name="workflow_completo",
        initial_input=task,
        context={"setor": "tecnologia", "prazo": "6 meses"}
    )
    
    if result.get('success'):
        print(f"✓ Workflow concluído com {len(result.get('results', []))} etapas")
        
        for i, step in enumerate(result.get('results', []), 1):
            print(f"  Etapa {i} - {step['step_name']}:")
            print(f"    Orquestrador: {step['orchestrator']}")
            print(f"    Sucesso: {step['result'].get('success', False)}")
        
        print(f"\n🎯 Resultado Final do Workflow: {result.get('final_output', 'N/A')}")
    else:
        print(f"❌ Erro no workflow: {result.get('error', 'Desconhecido')}")


async def demo_metrics_and_status(system):
    """Demonstra métricas e status do sistema"""
    print("\n📈 Demonstração: Métricas e Status")
    print("-" * 40)
    
    # Status do sistema
    status = system.get_system_status()
    print("📊 Status do Sistema:")
    print(f"  - Agentes: {status['agents_count']}")
    print(f"  - Orquestradores: {status['orchestrators_count']}")
    print(f"  - Agentes disponíveis: {', '.join(status['available_agents'])}")
    
    # Métricas
    metrics = system.get_metrics()
    print("\n📈 Métricas:")
    print(f"  - Total de orquestrações: {metrics['orchestrations_count']}")
    print(f"  - Sucessos: {metrics['successful_orchestrations']}")
    print(f"  - Falhas: {metrics['failed_orchestrations']}")
    print(f"  - Tempo médio: {metrics['average_execution_time']:.2f}s")
    
    if metrics['patterns_usage']:
        print("  - Padrões mais usados:")
        for pattern, count in metrics['patterns_usage'].items():
            print(f"    * {pattern}: {count} vezes")
    
    if metrics['agents_usage']:
        print("  - Agentes mais ativos:")
        for agent, count in metrics['agents_usage'].items():
            print(f"    * {agent}: {count} execuções")


async def run_complete_demo():
    """Executa demonstração completa do sistema"""
    print("🚀 Demonstração Completa do Sistema de Orquestração de Agentes")
    print("=" * 70)
    
    try:
        # Cria sistema de demonstração
        system = await create_demo_system()
        
        # Demonstrações
        await demo_sequential_orchestration(system)
        await demo_concurrent_orchestration(system)
        await demo_workflow(system)
        await demo_metrics_and_status(system)
        
        # Finaliza
        await system.shutdown()
        
        print("\n" + "=" * 70)
        print("🎉 Demonstração concluída com sucesso!")
        print("\n💡 Próximos passos:")
        print("1. Configure OPENAI_API_KEY para usar agentes reais")
        print("2. Execute 'python web_interface.py' para interface web")
        print("3. Personalize agentes e padrões conforme necessário")
        
    except Exception as e:
        print(f"\n❌ Erro na demonstração: {str(e)}")


if __name__ == "__main__":
    # Executa demonstração
    asyncio.run(run_complete_demo())

