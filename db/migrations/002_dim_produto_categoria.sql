-- Produto, categoria e subcategoria descrevem o mesmo objeto (o ativo de TI
-- impactado e a natureza da falha), por isso ficam em uma única dimensão em
-- vez de três separadas — evita joins triplos no dashboard sem ganho analítico.
-- Grão: 1 linha por combinação distinta de (produto, categoria, subcategoria).
CREATE TABLE IF NOT EXISTS dw.dim_produto_categoria (
    dim_produto_categoria_sk text PRIMARY KEY,
    produto text NOT NULL,
    categoria text NOT NULL,
    subcategoria text NOT NULL
);
