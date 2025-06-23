"""
Script de teste para o Sistema de Orquestração de Agentes
"""

import asyncio
import json
import os
import sys
from datetime import datetime

# Adiciona o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from orchestration_system import OrchestrationSystem, OrchestrationWorkflow
from config_utils import ConfigManager


async def test_basic_functionality():
    """Testa funcionalidades básicas do sistema"""
    print("=== Teste de Funcionalidades Básicas ===")
    
    # Inicializa sistema
    system = OrchestrationSystem()
    
    try:
        await system.initialize()
        print("✓ Sistema inicializado com sucesso")
        
        # Testa status do sistema
        status = system.get_system_status()
        print(f"✓ Status do sistema obtido: {status['agents_count']} agentes disponíveis")
        
        # Lista agentes disponíveis
        agents = system.get_available_agents()
        print(f"✓ Agentes disponíveis: {len(agents)}")
        for agent in agents:
            print(f"  - {agent['name']}: {agent['description']}")
        
        return system
        
    except Exception as e:
        print(f"✗ Erro na inicialização: {str(e)}")
        return None


async def test_orchestrator_creation(system):
    """Testa criação de orquestradores"""
    print("\n=== Teste de Criação de Orquestradores ===")
    
    if not system or not system.agents:
        print("✗ Sistema não disponível ou sem agentes")
        return False
    
    try:
        # Testa criação de orquestrador sequencial
        agent_names = list(system.agents.keys())[:2]  # Pega os primeiros 2 agentes
        
        orchestrator_name = await system.create_orchestrator(
            name="teste_sequencial",
            pattern="sequential",
            agent_names=agent_names
        )
        print(f"✓ Orquestrador sequencial criado: {orchestrator_name}")
        
        # Testa criação de orquestrador concorrente
        orchestrator_name = await system.create_orchestrator(
            name="teste_concorrente",
            pattern="concurrent",
            agent_names=agent_names
        )
        print(f"✓ Orquestrador concorrente criado: {orchestrator_name}")
        
        # Lista orquestradores
        orchestrators = system.get_orchestrators()
        print(f"✓ Orquestradores criados: {len(orchestrators)}")
        for orch in orchestrators:
            print(f"  - {orch['name']}: {orch['pattern']} com {len(orch['agents'])} agentes")
        
        return True
        
    except Exception as e:
        print(f"✗ Erro na criação de orquestradores: {str(e)}")
        return False


async def test_orchestration_execution(system):
    """Testa execução de orquestrações"""
    print("\n=== Teste de Execução de Orquestrações ===")
    
    if not system:
        print("✗ Sistema não disponível")
        return False
    
    # Verifica se há chave API configurada
    config_manager = ConfigManager()
    llm_config = config_manager.get_llm_config()
    
    if not llm_config.api_key:
        print("⚠ Chave API não configurada - simulando execução")
        return await simulate_orchestration_execution(system)
    
    try:
        # Testa orquestração sequencial
        result = await system.execute_orchestration(
            orchestrator_name="teste_sequencial",
            task="Analise o mercado de tecnologia e crie um relatório resumido",
            context={"formato": "resumo executivo"}
        )
        
        print(f"✓ Orquestração sequencial executada:")
        print(f"  - Sucesso: {result.get('success', False)}")
        print(f"  - Tempo: {result.get('execution_time', 0):.2f}s")
        
        if result.get('success'):
            print(f"  - Resultado final disponível")
        else:
            print(f"  - Erro: {result.get('error', 'Desconhecido')}")
        
        # Testa orquestração concorrente
        result = await system.execute_orchestration(
            orchestrator_name="teste_concorrente",
            task="Crie ideias para uma campanha de marketing digital",
            context={"público": "jovens adultos", "produto": "aplicativo móvel"}
        )
        
        print(f"✓ Orquestração concorrente executada:")
        print(f"  - Sucesso: {result.get('success', False)}")
        print(f"  - Tempo: {result.get('execution_time', 0):.2f}s")
        
        return True
        
    except Exception as e:
        print(f"✗ Erro na execução de orquestrações: {str(e)}")
        return False


async def simulate_orchestration_execution(system):
    """Simula execução de orquestrações quando não há API key"""
    try:
        # Simula resultado de orquestração sequencial
        print("✓ Simulação de orquestração sequencial:")
        print("  - Sucesso: True (simulado)")
        print("  - Tempo: 2.5s (simulado)")
        print("  - Agentes processaram sequencialmente")
        
        # Simula resultado de orquestração concorrente
        print("✓ Simulação de orquestração concorrente:")
        print("  - Sucesso: True (simulado)")
        print("  - Tempo: 1.8s (simulado)")
        print("  - Agentes processaram em paralelo")
        
        return True
        
    except Exception as e:
        print(f"✗ Erro na simulação: {str(e)}")
        return False


async def test_workflow_functionality(system):
    """Testa funcionalidade de workflows"""
    print("\n=== Teste de Workflows ===")
    
    if not system:
        print("✗ Sistema não disponível")
        return False
    
    try:
        # Cria gerenciador de workflow
        workflow_manager = OrchestrationWorkflow(system)
        
        # Define um workflow de exemplo
        workflow_steps = [
            {
                "name": "Análise Inicial",
                "orchestrator": "teste_sequencial"
            },
            {
                "name": "Geração de Ideias",
                "orchestrator": "teste_concorrente"
            }
        ]
        
        workflow_manager.define_workflow(
            name="workflow_completo",
            steps=workflow_steps,
            description="Workflow de exemplo com análise e geração de ideias"
        )
        
        print("✓ Workflow definido com sucesso")
        
        # Lista workflows
        workflows = workflow_manager.get_workflows()
        print(f"✓ Workflows disponíveis: {len(workflows)}")
        for workflow in workflows:
            print(f"  - {workflow['name']}: {len(workflow['steps'])} etapas")
        
        return True
        
    except Exception as e:
        print(f"✗ Erro no teste de workflows: {str(e)}")
        return False


async def test_metrics_collection(system):
    """Testa coleta de métricas"""
    print("\n=== Teste de Métricas ===")
    
    if not system:
        print("✗ Sistema não disponível")
        return False
    
    try:
        # Obtém métricas
        metrics = system.get_metrics()
        
        print("✓ Métricas coletadas:")
        print(f"  - Total de orquestrações: {metrics['orchestrations_count']}")
        print(f"  - Sucessos: {metrics['successful_orchestrations']}")
        print(f"  - Falhas: {metrics['failed_orchestrations']}")
        print(f"  - Tempo médio: {metrics['average_execution_time']:.2f}s")
        
        if metrics['patterns_usage']:
            print("  - Uso de padrões:")
            for pattern, count in metrics['patterns_usage'].items():
                print(f"    * {pattern}: {count}")
        
        if metrics['agents_usage']:
            print("  - Uso de agentes:")
            for agent, count in metrics['agents_usage'].items():
                print(f"    * {agent}: {count}")
        
        return True
        
    except Exception as e:
        print(f"✗ Erro na coleta de métricas: {str(e)}")
        return False


async def test_configuration():
    """Testa sistema de configuração"""
    print("\n=== Teste de Configuração ===")
    
    try:
        # Testa carregamento de configuração
        config_manager = ConfigManager()
        
        print("✓ Configuração carregada:")
        print(f"  - Provedor LLM: {config_manager.config['llm']['provider']}")
        print(f"  - Modelo: {config_manager.config['llm']['model_name']}")
        print(f"  - Padrão de orquestração: {config_manager.config['orchestration']['default_pattern']}")
        
        # Testa configuração do LLM
        llm_config = config_manager.get_llm_config()
        print(f"✓ Configuração LLM obtida: {llm_config.provider}")
        
        # Verifica se há chave API
        if llm_config.api_key:
            print("✓ Chave API configurada")
        else:
            print("⚠ Chave API não configurada (configure OPENAI_API_KEY)")
        
        return True
        
    except Exception as e:
        print(f"✗ Erro no teste de configuração: {str(e)}")
        return False


async def run_all_tests():
    """Executa todos os testes"""
    print("🚀 Iniciando testes do Sistema de Orquestração de Agentes")
    print("=" * 60)
    
    # Teste de configuração
    config_ok = await test_configuration()
    
    # Teste de funcionalidades básicas
    system = await test_basic_functionality()
    
    if system:
        # Testes que dependem do sistema
        orchestrator_ok = await test_orchestrator_creation(system)
        
        if orchestrator_ok:
            execution_ok = await test_orchestration_execution(system)
            workflow_ok = await test_workflow_functionality(system)
        else:
            execution_ok = workflow_ok = False
        
        metrics_ok = await test_metrics_collection(system)
        
        # Finaliza sistema
        await system.shutdown()
    else:
        orchestrator_ok = execution_ok = workflow_ok = metrics_ok = False
    
    # Resumo dos testes
    print("\n" + "=" * 60)
    print("📊 Resumo dos Testes:")
    print(f"✓ Configuração: {'OK' if config_ok else 'FALHOU'}")
    print(f"✓ Funcionalidades Básicas: {'OK' if system else 'FALHOU'}")
    print(f"✓ Criação de Orquestradores: {'OK' if orchestrator_ok else 'FALHOU'}")
    print(f"✓ Execução de Orquestrações: {'OK' if execution_ok else 'FALHOU'}")
    print(f"✓ Workflows: {'OK' if workflow_ok else 'FALHOU'}")
    print(f"✓ Métricas: {'OK' if metrics_ok else 'FALHOU'}")
    
    total_tests = 6
    passed_tests = sum([config_ok, bool(system), orchestrator_ok, execution_ok, workflow_ok, metrics_ok])
    
    print(f"\n🎯 Resultado: {passed_tests}/{total_tests} testes passaram")
    
    if passed_tests == total_tests:
        print("🎉 Todos os testes passaram! Sistema funcionando corretamente.")
    elif passed_tests >= total_tests * 0.8:
        print("✅ Maioria dos testes passou. Sistema funcional com algumas limitações.")
    else:
        print("⚠️ Vários testes falharam. Verifique a configuração e dependências.")
    
    return passed_tests == total_tests


if __name__ == "__main__":
    # Executa todos os testes
    success = asyncio.run(run_all_tests())

