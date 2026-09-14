---
name: saturation
description: "Orquestrar uma implementação por meio de subagentes a partir do contexto atual da sessão. Usar quando o usuário invocar /saturation para implementar, revisar e reparar uma tarefa preservando sua intenção e escopo."
---

Ao iniciar `/saturation`, consolide o contexto ativo e `code_styleguides/SKILL.md`
em `.saturation/context.md`, registrando objetivo, escopo, qualidade, restrições,
decisões, princípios e critérios de verificação. Execute `/s-init` e confirme o
ambiente pronto antes da primeira delegação. Congele o contexto antes de delegar
e mantenha-o como fonte única durante todo o run; mudanças de intenção, escopo,
qualidade ou restrições exigem decisão explícita do usuário.

Divida o trabalho em assignments coerentes e disjuntos e use sessões novas:
toda escrita de produto é delegada a elas. Cada handoff inclui contexto,
assignment, estado e evidências; implementadores e reparadores escrevem somente
no assignment e reportam caminhos alterados, evidências e riscos. Para cada
assignment, isole um candidato a partir da última versão aprovada, inspecione o
diff e promova somente após revisão independente, dentro do escopo e contexto.
Preserve alterações externas que surgirem ou conflitarem durante o run e escale
ao usuário a decisão sobre elas.

Após cada implementação, use reviewer fresco, adversarial e read-only, que aprove
somente com evidência independente. Repita `implementar → revisar → reparar →
verificar` até a revisão mais recente não apontar gaps materiais e a verificação
demonstrar todos os critérios de verificação; então faça a consolidação final.

Resolva internamente decisões técnicas, sequência, assignments, agentes,
pesquisa, testes e reparos. Decisões sobre intenção, escopo, qualidade,
restrições, conflitos, operações de dados, efeitos reais e blockers pertencem
ao usuário: escale-as e aguarde quando necessário. Centralize a comunicação:
consolide os reports dos subagentes para o usuário somente após esses gates.
