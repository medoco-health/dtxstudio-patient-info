COPY (
    SELECT p.object_id, p.dob, p.last_name, p.first_name, p.middle_initial, 
           UPPER(gt.permanent_label) as gender, p.custom_identifier, p.person_id, p.ssn
    FROM patients p
    LEFT JOIN gender_types gt ON gt.type_id = p.gender_id
) TO '/tmp/patients_export.csv' 
WITH CSV HEADER;