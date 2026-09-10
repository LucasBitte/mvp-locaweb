-- duracao_horas pertence ao mart para auditoria/rótulo, mas não às features
-- do treino. Essa exclusão é verificada no teste Python do notebook real.
select incident_id
from {{ source('ml', 'ml_sla_classification_dataset') }}
where prioridade_num is null
   or hora_abertura not between 0 and 23
   or mes_abertura not between 1 and 12
   or dia_semana_num not between 0 and 6
   or target_excedeu_tempo is null
