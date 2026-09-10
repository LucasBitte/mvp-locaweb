-- Mesmo grão e população da base; clustering é descritivo, não preditivo.
select coalesce(b.incident_id, c.incident_id, s.incident_id) as incident_id
from {{ source('ml', 'ml_base_features') }} b
full join {{ source('ml', 'ml_cluster_dataset') }} c using (incident_id)
full join {{ source('ml', 'ml_sla_classification_dataset') }} s using (incident_id)
where b.incident_id is null or c.incident_id is null or s.incident_id is null
