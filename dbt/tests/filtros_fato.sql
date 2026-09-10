select f.incident_id
from {{ source('dw', 'fct_incidentes') }} f
left join {{ source('dw', 'dim_status') }} s using (dim_status_sk)
where f.aberto_at < timestamp '2025-01-01'
   or s.status = 'Sem Intervenção'
   or s.dim_status_sk is null
