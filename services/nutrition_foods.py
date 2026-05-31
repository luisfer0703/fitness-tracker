"""Alimentos recomendados según perfil y objetivo del usuario."""


def _objetivo_nutricional(peso_actual, objetivo_peso):
    if not peso_actual or not objetivo_peso:
        return "mantener"
    if objetivo_peso < peso_actual - 1:
        return "bajar"
    if objetivo_peso > peso_actual + 1:
        return "subir"
    return "mantener"


def alimentos_recomendados(peso_actual, objetivo_peso, actividad, imc, categoria_imc, proteina_g=None):
    objetivo = _objetivo_nutricional(peso_actual, objetivo_peso)
    actividad = actividad or "media"

    labels = {
        "bajar": "Pérdida de peso (déficit moderado)",
        "subir": "Ganancia de peso / masa muscular",
        "mantener": "Mantenimiento y composición corporal",
    }

    # Base por objetivo
    if objetivo == "bajar":
        proteinas = [
            {"nombre": "Pechuga de pollo o pavo", "porcion": "150 g", "nota": "Alta proteína, baja grasa"},
            {"nombre": "Huevos enteros", "porcion": "2-3 unidades", "nota": "Saciedad y proteína"},
            {"nombre": "Atún o salmón", "porcion": "120-150 g", "nota": "Omega-3 y proteína"},
            {"nombre": "Yogur griego natural", "porcion": "170 g", "nota": "Proteína sin azúcar añadida"},
            {"nombre": "Tofu firme", "porcion": "150 g", "nota": "Opción vegetal"},
        ]
        carbos = [
            {"nombre": "Avena", "porcion": "40-50 g", "nota": "Fibra, energía sostenida"},
            {"nombre": "Arroz integral o quinoa", "porcion": "50-70 g cocido", "nota": "Porción controlada"},
            {"nombre": "Batata", "porcion": "150 g", "nota": "Mejor que harinas refinadas"},
            {"nombre": "Legumbres (lentejas, garbanzos)", "porcion": "1 taza cocida", "nota": "Fibra + proteína vegetal"},
        ]
        grasas = [
            {"nombre": "Aguacate", "porcion": "1/4 unidad", "nota": "Grasas saludables en moderación"},
            {"nombre": "Aceite de oliva", "porcion": "1 cda", "nota": "Condimentar ensaladas"},
            {"nombre": "Nueces o almendras", "porcion": "15-20 g", "nota": "Snack controlado"},
        ]
        verduras = [
            {"nombre": "Ensalada mixta (lechuga, tomate, pepino)", "porcion": "plato libre", "nota": "Volumen con pocas kcal"},
            {"nombre": "Brócoli o espárragos", "porcion": "200 g", "nota": "Fibra y micronutrientes"},
            {"nombre": "Espinacas salteadas", "porcion": "2 tazas", "nota": "Hierro y saciedad"},
        ]
        evitar = ["Refrescos y jugos azucarados", "Frituras y comida rápida", "Pan/blanco y bollería diaria", "Alcohol frecuente"]
    elif objetivo == "subir":
        proteinas = [
            {"nombre": "Carne magra (res, pollo)", "porcion": "180-200 g", "nota": "Base para ganar masa"},
            {"nombre": "Huevos", "porcion": "3-4 unidades", "nota": "Proteína y grasas"},
            {"nombre": "Salmón o caballa", "porcion": "150 g", "nota": "Calorías de calidad"},
            {"nombre": "Batido de leche + whey (opcional)", "porcion": "1 vaso", "nota": "Post-entreno"},
            {"nombre": "Queso cottage o ricotta", "porcion": "150 g", "nota": "Caseína y snacks"},
        ]
        carbos = [
            {"nombre": "Arroz blanco o pasta integral", "porcion": "80-100 g cocido", "nota": "Energía para entrenar"},
            {"nombre": "Avena con fruta", "porcion": "60 g + plátano", "nota": "Desayuno calórico"},
            {"nombre": "Pan integral", "porcion": "2 rebanadas", "nota": "Con proteína en comidas"},
            {"nombre": "Miel o dátiles", "porcion": "post-entreno", "nota": "Recuperación rápida"},
        ]
        grasas = [
            {"nombre": "Aguacate", "porcion": "1/2 unidad", "nota": "Calorías densas"},
            {"nombre": "Mantequilla de maní natural", "porcion": "2 cdas", "nota": "Snack calórico"},
            {"nombre": "Aceite de oliva", "porcion": "2 cdas/día", "nota": "Sumar calorías saludables"},
        ]
        verduras = [
            {"nombre": "Verduras variadas", "porcion": "2-3 tazas/día", "nota": "No omitir micronutrientes"},
            {"nombre": "Batata asada", "porcion": "200 g", "nota": "Carbohidrato pre-entreno"},
        ]
        evitar = ["Solo comida ultraprocesada", "Saltarse comidas", "Exceso de alcohol"]
    else:
        proteinas = [
            {"nombre": "Pollo, pescado o huevos", "porcion": "150 g / 2-3 uds", "nota": "Proteína en cada comida principal"},
            {"nombre": "Legumbres", "porcion": "1 taza", "nota": "2-3 veces por semana"},
            {"nombre": "Yogur o queso bajo en grasa", "porcion": "1 porción", "nota": "Snack proteico"},
        ]
        carbos = [
            {"nombre": "Cereales integrales", "porcion": "porción estándar", "nota": "Energía estable"},
            {"nombre": "Fruta de temporada", "porcion": "2-3 piezas/día", "nota": "Vitaminas y fibra"},
            {"nombre": "Arroz, pasta o quinoa", "porcion": "1/2 plato", "nota": "Balance con proteína"},
        ]
        grasas = [
            {"nombre": "Frutos secos", "porcion": "un puñado", "nota": "Grasas buenas"},
            {"nombre": "Aceite de oliva", "porcion": "1-2 cdas", "nota": "Cocinar y ensaladas"},
        ]
        verduras = [
            {"nombre": "Verduras al vapor o ensalada", "porcion": "1/2 plato", "nota": "En almuerzo y cena"},
        ]
        evitar = ["Exceso de ultraprocesados", "Comidas muy irregulares"]

    if actividad == "alta" and objetivo != "bajar":
        carbos.append({"nombre": "Plátano o dátiles", "porcion": "1-2 uds", "nota": "Extra si entrenas fuerte"})

    if categoria_imc and "bajo" in (categoria_imc or "").lower():
        carbos.insert(0, {"nombre": "Batidos o frutos secos", "porcion": "entre comidas", "nota": "Subir calorías saludables"})

    categorias = [
        {"id": "proteinas", "titulo": "🥩 Proteínas prioritarias", "lista": proteinas},
        {"id": "carbos", "titulo": "🍚 Carbohidratos", "lista": carbos},
        {"id": "verduras", "titulo": "🥗 Verduras y fibra", "lista": verduras},
        {"id": "grasas", "titulo": "🥑 Grasas saludables", "lista": grasas},
    ]

    return {
        "objetivo": objetivo,
        "objetivo_label": labels[objetivo],
        "categorias": categorias,
        "evitar": evitar,
        "tip_proteina": f"Objetivo diario de proteína: ~{proteina_g} g" if proteina_g else None,
    }


def comidas_del_dia(peso_actual, objetivo_peso, actividad, proteina_g=None):
    """Tres comidas ejemplo según objetivo del usuario."""
    objetivo = _objetivo_nutricional(peso_actual, objetivo_peso)
    actividad = actividad or "media"

    menus = {
        "bajar": {
            "desayuno": {
                "titulo": "Desayuno",
                "icono": "🌅",
                "platos": [
                    {"nombre": "Avena + yogur griego + frutos rojos", "nota": "Proteína y fibra"},
                    {"nombre": "Huevo cocido o revuelto (2 uds)", "nota": "Saciedad"},
                    {"nombre": "Té o café sin azúcar", "nota": "Hidratación"},
                ],
            },
            "comida": {
                "titulo": "Comida",
                "icono": "☀️",
                "platos": [
                    {"nombre": "Pechuga de pollo o pescado (150 g)", "nota": "Proteína magra"},
                    {"nombre": "Ensalada grande + 1/2 taza arroz integral", "nota": "Volumen controlado"},
                    {"nombre": "Verduras al vapor", "nota": "Fibra"},
                ],
            },
            "cena": {
                "titulo": "Cena",
                "icono": "🌙",
                "platos": [
                    {"nombre": "Tortilla de claras + verduras", "nota": "Ligera y proteica"},
                    {"nombre": "Sopa de verduras o caldo", "nota": "Pocas kcal"},
                    {"nombre": "Infusión o agua", "nota": "Evita líquidos calóricos"},
                ],
            },
        },
        "subir": {
            "desayuno": {
                "titulo": "Desayuno",
                "icono": "🌅",
                "platos": [
                    {"nombre": "Avena 60 g + plátano + mantequilla de maní", "nota": "Calorías de calidad"},
                    {"nombre": "3 huevos enteros", "nota": "Proteína y grasas"},
                    {"nombre": "Vaso de leche o batido", "nota": "Extra calórico"},
                ],
            },
            "comida": {
                "titulo": "Comida",
                "icono": "☀️",
                "platos": [
                    {"nombre": "Carne o pollo (180 g) + arroz/pasta", "nota": "Comida principal"},
                    {"nombre": "Aguacate o aceite de oliva", "nota": "Grasas saludables"},
                    {"nombre": "Verduras variadas", "nota": "Micronutrientes"},
                ],
            },
            "cena": {
                "titulo": "Cena",
                "icono": "🌙",
                "platos": [
                    {"nombre": "Salmón o atún (150 g)", "nota": "Proteína nocturna"},
                    {"nombre": "Batata o pan integral", "nota": "Carbohidratos"},
                    {"nombre": "Queso cottage o yogur", "nota": "Snack proteico"},
                ],
            },
        },
        "mantener": {
            "desayuno": {
                "titulo": "Desayuno",
                "icono": "🌅",
                "platos": [
                    {"nombre": "Huevos + pan integral + fruta", "nota": "Balanceado"},
                    {"nombre": "Yogur natural con nueces", "nota": "Proteína y grasas"},
                ],
            },
            "comida": {
                "titulo": "Comida",
                "icono": "☀️",
                "platos": [
                    {"nombre": "Proteína (pollo/pescado/huevos) 150 g", "nota": "Base del plato"},
                    {"nombre": "Carbohidrato integral (1/2 plato)", "nota": "Energía estable"},
                    {"nombre": "Verduras (1/2 plato)", "nota": "Fibra y vitaminas"},
                ],
            },
            "cena": {
                "titulo": "Cena",
                "icono": "🌙",
                "platos": [
                    {"nombre": "Pescado o legumbres + ensalada", "nota": "Ligera pero completa"},
                    {"nombre": "Fruta de temporada", "nota": "Postre natural"},
                ],
            },
        },
    }

    menu = menus.get(objetivo, menus["mantener"])
    if actividad == "alta" and objetivo != "bajar":
        menu["comida"]["platos"].append(
            {"nombre": "Plátano o dátiles", "nota": "Extra si entrenaste hoy"}
        )

    return [menu["desayuno"], menu["comida"], menu["cena"]]
