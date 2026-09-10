select count(*) as quantidade
from {{ source('dw', 'fct_incidentes') }}
having count(*) = 0
