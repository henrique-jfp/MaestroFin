from dataclasses import dataclass
from datetime import datetime

from gerente_financeiro.wrapped_anual import (
    derive_lancamento_meta,
    infer_category_from_description,
    infer_payment_method,
)


@dataclass
class DummyCategoria:
    nome: str


@dataclass
class DummyLancamento:
    tipo: str = ''
    categoria: DummyCategoria | None = None
    descricao: str | None = None
    meio_pagamento: str | None = None
    origem: str | None = None
    valor: float = 0.0
    data_transacao: datetime = datetime.now()


def test_infer_category_from_description_ifood():
    assert infer_category_from_description('Compra iFood do almoço') == 'Alimentação'


def test_infer_payment_method_pix_and_card():
    assert infer_payment_method('PIX', None) == 'Pix'
    assert infer_payment_method('Cartao Visa', 'Pagamento com Visa') == 'Cartão de Crédito'
    assert infer_payment_method(None, 'boleto bancario') == 'Boleto'


def test_derive_lancamento_meta_prefers_inferred_when_categoria_receita_on_despesa():
    # Caso onde categoria registrada diz 'Receitas' mas tipo é 'Despesa' -> usar inferência
    lanc = DummyLancamento(
        tipo='Despesa',
        categoria=DummyCategoria(nome='Receitas Extras'),
        descricao='Compra no mercado',
        meio_pagamento='cartao debito',
        valor=123.45
    )

    tipo_eff, categoria_eff, metodo = derive_lancamento_meta(lanc)
    assert tipo_eff in ('Despesa', 'Receita')
    # A inferência deve reconhecer 'mercado' -> Alimentação
    assert categoria_eff == 'Alimentação'
    assert metodo.lower().startswith('cart') or metodo == 'Cartão' or metodo == 'Cartão de Crédito'
