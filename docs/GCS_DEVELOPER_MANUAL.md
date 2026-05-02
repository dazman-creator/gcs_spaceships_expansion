# GCS Spaceships Developer Manual

Este documento imortaliza todo o conhecimento técnico, estrutura de dados JSON do GURPS Character Sheet (GCS) v5, e lições aprendidas durante o desenvolvimento da biblioteca automatizada GURPS Spaceships 1 a 8.

## 1. Lições Críticas sobre a Arquitetura JSON do GCS v5

### 1.1. Armaduras e Hit Locations (`dr_bonus`)
Diferente das edições anteriores, onde armaduras podiam ter atributos diretos, no GCS 5, bônus de equipamento usam a array `features`.
*   Para adicionar DR através de um módulo de nave (Equipamento), você **não** usa a tag `dr`. Você injeta um `dr_bonus` apontando exatamente para o ID da hit location estabelecido no arquivo `.body` da nave.
*   **Regra de Ouro:** A string de `location` no `dr_bonus` (ex: `"front"`) DEVE bater de forma exata com a string `id` da Hit Location no `.body`. Se diferir, o GCS ignora a armadura.
*   **Sintaxe Correta:**
```json
"features": [
  {
    "type": "dr_bonus",
    "location": "front",
    "amount": 300
  }
]
```

### 1.2. Equipamentos e Containers (O Bug do Escudo)
*   Equipamentos devem obrigatoriamente possuir a propriedade `"equipped": true` no seu nó raiz do JSON. Sem isso, seus *features* não são carregados na ficha.
*   **A Pegadinha do Container:** Se você guardar módulos de nave dentro de um `equipment_container` (ex: "Front Hull Section"), **o container pai também DEVE possuir a propriedade `"equipped": true`**. Se o container estiver inativo, todos os seus filhos serão desativados em cascata pelo GCS, anulando armaduras e armas.

### 1.3. Armas de Ranged Attack (O Bug da Bateria Fantasma)
As armas de longo alcance (Ranged Weapons) anexadas a equipamentos (como Baterias ou Lasers) requerem um bloco `"weapons": []` dentro do JSON do equipamento.
*   **O Erro Fatal:** O GCS 5 *exige* que toda arma declarada tenha um **UUID válido** dentro do bloco da arma. Se faltar a chave `"id"`, a arma **NÃO APARECERÁ** na tabela de "Ranged Attacks" da ficha.
*   **A Sintaxe do Dano:** Multiplicadores de dano em GCS usam a letra minúscula `x` (ex: `3dx50`). O uso de asterisco (`3d*50`) causa erros de parser.
*   **Sintaxe Correta:**
```json
"weapons": [
  {
    "id": "e45f9a...", // OBRIGATÓRIO!
    "type": "ranged_weapon",
    "damage": {"type": "pi", "base": "3dx50", "armor_divisor": 1},
    "usage": "Generic Gun/Beam",
    "accuracy": "0",
    "range": "Space",
    "rate_of_fire": "1"
  }
]
```

### 1.4. Massa e Suporte de Carga (O Hack do Lifting ST)
GURPS Spaceships é medido em toneladas massivas, o que quebra o *Basic Lift* normal do GURPS. A solução engenhosa adotada:
*   Os módulos de **Chassis** foram modelados como *Traits* (`.adq`).
*   Usamos a vantagem oficial **Lifting ST** acoplada ao chassis da nave. A equação usada para calcular o nível de Lifting ST com base na Loaded Mass da nave (em toneladas):
    *   Massa em Lbs = Loaded Mass * 2000
    *   Target Basic Lift = Massa / 2
    *   **Lifting ST = Raiz Quadrada de (Target Basic Lift * 5)**
Isso faz com que o inventário da ficha calcule a capacidade de peso perfeitamente sem erros vermelhos no GCS.

---

## 2. A Automação (Ferramentas no Repositório)

### 2.1. O Gerador Aleatório (`generate_random_ship.py`)
Criado para Game Masters produzirem frotas massivas em segundos.
*   Lê bibliotecas (`Spaceships - Modules.eqp`, `Chassis.adq`, `Spaceship.body`).
*   Carrega um "boiler plate" de ficha do GCS vazio.
*   Implementa perfis rígidos de 20 slots de casco (6 Front / 6 Center / 6 Rear / 2 Core).
*   Gera UUIDs fresquinhos recursivamente para cada módulo extraído para não bugar a biblioteca do GCS com chaves duplicadas.

### 2.2. A Suite de Testes TDD (`test_generator.py`)
Qualquer modificação na biblioteca de Spaceships deve passar por este escrutínio.
*   Gera rapidamente 500+ naves.
*   Abre os `.gcs` gerados e verifica:
    *   Se todos os containers e itens possuem `"equipped": true`.
    *   Se o total de peças no casco somam matematicamente 20 slots exatos.
    *   Se nenhum UUID de equipamento duplicou.
    *   Se todas as propriedades de `weapons` possuem `id`.
    *   Se os bônus de DR apontam para locations válidos.

## 3. Fluxo de Expansões Futuras (Livros 2 a 8)
Se você for invadir o território dos Livros 2-8 de Spaceships, use este repositório como alicerce:
1.  **Novos Módulos:** Converta as tabelas em JSON injetando no `Spaceships - Modules.eqp`. Preste muita atenção em criar UUIDs novos.
2.  **Testes:** Sempre rode o `test_generator.py` após atualizar o catálogo. Se você introduziu itens inválidos (ex: sem `id` nas armas ou sem `equipped`), o TDD barrará o erro antes que as fichas na sua campanha se corrompam.
