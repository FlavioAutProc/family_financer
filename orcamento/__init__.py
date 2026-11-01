"""Orçamento Familiar Pro — sistema de controle financeiro familiar.

Camadas:
    modelos     -> entidades (dataclasses) e configurações
    banco       -> persistência em SQLite
    motor       -> projeção de 36 meses (cálculo puro, sem I/O)
    analises    -> controle, cortes, reserva, dívidas, extras/provisões, histórico...
    importador  -> leitura da planilha Excel original
    exportador  -> Excel, JSON e PDF (folha de anotações A4)
    ui          -> telas Streamlit
"""

__version__ = "1.0.0"
