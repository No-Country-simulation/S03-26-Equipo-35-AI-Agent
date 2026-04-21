"""Módulo de agentes multi-agente para AutoStory Builder.

Arquitectura LangGraph:
  [RAG] → [Analista de Contexto] → [Escritor Especializado]
                                           ↓
                                    [Editor QA]
                                   ↙          ↘
                             Aprobado      Rechazado (feedback)
                                ↓               ↓ (máx 2 reintentos)
                          [Finalizar]     [Escritor] → [Editor QA]
                                                ↓
                                          [Finalizar]
"""
