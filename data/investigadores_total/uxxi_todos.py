import pandas as pd
import json

consulta = """
select distinct
    ter00.strnombre as nombre,
    ter00.str1apellido as apellido1,
    ter00.str2apellido as apellido2,
    ter00.stremail as email
from
    uxxiinv.tbinvgenidentidadtercero ter00,
    uxxiinv.tbinvgentipodocidentidad tdoc00
where
    ter00.numidtipodoc = tdoc00.numidtipodoc(+)
and ter00.blninvestigador = 1
and tdoc00.strcodigo = 'NIF'
"""

limit = 10000
offset = 0
bloques = []

while True:
    df_bloque = api_post_df(
        api_sql,
        SQL_URL,
        consulta,
        binds={},
        limit=limit,
        offset=offset
    )

    bloques.append(df_bloque)

    print(
        f"Offset {offset}: "
        f"{len(df_bloque)} investigadores recuperados"
    )

    if len(df_bloque) < limit:
        break

    offset += limit

df_investigadores = pd.concat(
    bloques,
    ignore_index=True
).drop_duplicates()

print(f"Total recuperado: {len(df_investigadores)}")

df_investigadores.to_json(
    "todos_investigadores.json",
    orient="records",
    indent=2,
    force_ascii=False
)