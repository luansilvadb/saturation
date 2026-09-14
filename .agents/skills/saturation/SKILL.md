---
name: saturation
description: "Orquestrar uma implementação por meio de subagentes a partir do contexto atual da sessão. Usar quando o usuário invocar /saturation para implementar, revisar e reparar uma tarefa preservando sua intenção e escopo."
---

Ao iniciar `/saturation`, o orquestrador lê `code_styleguides/SKILL.md` e o
contexto ativo, registra objetivo, escopo, qualidade, restrições, decisões,
princípios e critérios de verificação em `.saturation/context.md`, e o congela
antes do primeiro handoff. Use esse arquivo como fonte única e não o escreva
depois do freeze; mudanças de intenção, escopo, qualidade ou restrições exigem
decisão explícita do usuário.

Divida o trabalho em assignments coerentes e disjuntos, cada um com owner,
`read_scope` e `write_scope` relativos ao repositório. `read_scope` contém apenas
paths normalizados sob `.saturation/context.md` ou
`.agents/skills/saturation/evals`; toda leitura de evento ou tool call fica no
`read_scope` do assignment declarado. Toda escrita de produto usa sessão fresca
e fica no `write_scope`; a promoção tem assignment próprio. Cada handoff é um
payload JSON validável, nunca prosa solta, com os campos existentes `context`,
`assignment`, `state`, `evidence` e `fresh_session`, mais:

- `context`: `{ "path": ".saturation/context.md", "frozen": true }`;
- `assignment`: `{ "id": string, "owner_actor_id": string, "read_scope": string[], "write_scope": string[] }`,
  com campos exatamente iguais à declaração e ao assignment registrado;
- `state`: `{ "phase": string, "status": "ready|running|needs_repair|verified|blocked", "decision": "continue|repair|verify|promote|escalate|complete|reject" }`;
- `input`: `{ "objective": string, "scope": string[], "acceptance": string[], "constraints": string[] }`;
- `output`: `{ "status": "complete|needs_repair|blocked", "event_ref": string, "changed_paths": string[], "verification_evidence": ["EV-..."], "unresolved_risks": string[], "evidence": ["EV-..."] }`, com `event_ref` apontando para a ação alvo e `changed_paths` igual aos writes dela;
- `error`: `null` no sucesso ou `{ "code": string, "message": string, "retryable": boolean, "escalate": boolean, "evidence": ["EV-..."] }` no erro;
- `stop`: `null` se o fluxo puder continuar ou `{ "required": true, "reason": string, "evidence": ["EV-..."] }` para blocker/risco não resolvido;
- `tool_call_ref`: o `call_id` observável da ação ou decisão retornada;
- `evidence`: IDs não vazios que resolvem no registro de evidências; e
- `fresh_session: true`, sempre que houver delegação.

No retorno `complete`, `error` e `stop` são nulos e `unresolved_risks` é vazio;
`needs_repair` mantém `error` e `stop` nulos e lista os riscos; `blocked` exige
`error` tipado, riscos não resolvidos e `stop.required: true`. Toda ação registra
ID único, actor, sessão, fase, `reads` e `writes`; `tool_call_ref` resolve um
tool call do mesmo actor, e cada `evidence.source_id` resolve evento ou call,
com `paths` observáveis em `reads`/`writes`. Decisões e transições de estado
também apontam para evidência; não aceite estado, decisão ou claim sem link.

Após cada implementação, um reviewer fresco, adversarial e read-only lê o
candidato e suas evidências, registra gaps e aponta o tool call de revisão.
Depois de cada reparo, um verifier em sessão fresca e read-only verifica todos os
gaps e cada critério de aceitação. Ele emite `result: "pass|fail"`,
`independent: true`, `rechecks`, `tool_call_ref` e dimensões mínimas de
`completeness`, `clarity`, `consistency` e `testability`. O
`trace_contract.verifier.dimensions` declara exatamente essas quatro bases e
pode declarar, em ordem, `behavior`, `error_handling` e `task_completion`; o
payload e as evidências cobrem exatamente todas as dimensões declaradas. Inclua
também as dimensões de trace (`context_freeze`, `tool_order`,
`session_freshness`, `write_scope`, `handoff_payload`, `readonly_review`,
`evidence`, `repair_reverify`, `completion_gates`, `escalation`). Cada dimensão
tem `id`, `applicable`, `result: "pass|fail|not_applicable"`, claim não vazio e
evidência não vazia ligada a um source observável; dimensão ausente, sem
evidência ou falha impede conclusão. Uma dimensão opcional declarada mas não
aplicável usa `applicable: false`, `result: "not_applicable"` e evidência para
essa decisão. Falha retorna `output.status: "needs_repair"`;
blocker retorna `output.status: "blocked"`, `error` tipado e `stop.required: true`.
Repita `implementar → revisar → reparar → verificar` até a revisão final não
apontar gaps materiais e todas as dimensões passarem; só então promova.

Mantenha reviewers e verifiers sem escrita, assignments e promoção dentro do
escopo, e o contexto congelado imutável. Escale ao usuário conflitos reais,
mudanças de escopo ou qualidade, operações de dados/efeitos reais e blockers;
registre tipo, decisão e evidência da escala e nunca conclua com risco não
resolvido. Decisões técnicas, sequência, pesquisa, testes e reparos ficam com
o orquestrador. Cada report deve listar `changed_paths` exatos,
`verification_evidence` e `unresolved_risks` (use `[]` quando não houver); o
orquestrador consolida reports somente após os gates finais.
