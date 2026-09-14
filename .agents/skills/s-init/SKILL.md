---
name: s-init
description: "Inicializar e verificar o ambiente de um repositório para uso com sessões novas de subagentes. Usar quando o usuário invocar /S-init ou precisar confirmar que a capacidade nativa de subagentes está disponível antes de uma esteira de implementação."
---

Prepare e valide o ambiente do repositório para uso com subagentes.

1. Identifique o repositório e o contexto operacional atual.
2. Use a capacidade nativa do terminal ou agente para iniciar uma sessão nova.
3. Execute uma sonda efêmera, somente leitura, com uma instrução simples.
4. Confirme a resposta, encerre a sessão e deixe o ambiente limpo.
5. Retorne um diagnóstico curto e objetivo.

Retorne `READY` quando a sessão nova responder e encerrar corretamente. Retorne
`NOT READY` quando a capacidade falhar ou estiver indisponível, descrevendo a
causa observada e o próximo passo para o usuário.
