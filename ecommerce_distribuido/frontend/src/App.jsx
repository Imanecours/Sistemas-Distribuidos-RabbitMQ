import { useState, useEffect } from 'react';

function Catalogo() {
  const [produtos, setProdutos] = useState([]);
  const [notificacoes, setNotificacoes] = useState([]);
  
  const [email, setEmail] = useState('');
  const [categorias, setCategorias] = useState({
    papelaria: false,
    escritorio: false,
    acessorios: false
  });

  const [quantidades, setQuantidades] = useState({});

  const handleQuantidadeChange = (id_produto, valor) => {
    setQuantidades({
      ...quantidades,
      [id_produto]: parseInt(valor) || 1
    });
  };

  useEffect(() => {
    fetch('http://localhost:5000/produtos')
      .then(res => res.json())
      .then(dados => setProdutos(dados))
      .catch(erro => console.error("erro ao carregar produtos:", erro));
  }, []);

  useEffect(() => {
    const eventSource = new EventSource('http://localhost:5000/stream');

    eventSource.onmessage = (event) => {
      const novaNotificacao = JSON.parse(event.data);

      if (novaNotificacao.link_pagamento) {
        window.open(novaNotificacao.link_pagamento, '_blank', 'noopener,noreferrer');
      }

      setNotificacoes((notificacoesAnteriores) => {
        const index = notificacoesAnteriores.findIndex(n => n.id_pedido === novaNotificacao.id_pedido);
        if (index >= 0) {
          const novaLista = [...notificacoesAnteriores];
          novaLista[index] = novaNotificacao;
          return novaLista;
        } else {
          return [...notificacoesAnteriores, novaNotificacao]; 
        }
      });
    };

    return () => eventSource.close();
  }, []);

  const cancelarPedido = (id_pedido) => {
    fetch(`http://localhost:5000/pedido/${id_pedido}`, {
      method: 'DELETE'
    })
    .then(res => res.json())
    .then(dados => console.log("Cancelamento:", dados))
    .catch(erro => console.error("Erro ao cancelar:", erro));
  };

  const comprarProduto = (id_produto) => {

    const qtd = quantidades[id_produto] || 1;

    fetch('http://localhost:5000/comprar', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ 
        id_produto: id_produto, 
        quantidade:  qtd
      })
    })
    .then(res => res.json())
    .then(dados => {
      console.log(dados);
    })
    .catch(erro => console.error("Erro ao comprar produto:", erro));
  };

  //funçao para enviar a inscriçao nas promoçoes
  const assinarPromocoes = (e) => {
    e.preventDefault(); // impede a pagina de recarregar
    
    const categoriasSelecionadas = Object.keys(categorias).filter(k => categorias[k]);
    
    fetch('http://localhost:5000/promocoes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email, categorias: categoriasSelecionadas })
    })
    .then(() => {
      alert("Inscrição realizada com sucesso!");
      setEmail(''); // Limpa o formulário
    })
    .catch(erro => console.error("Erro ao assinar:", erro));
  };

  const handleCategoriaChange = (e) => {
    setCategorias({
      ...categorias,
      [e.target.name]: e.target.checked
    });
  };

  return (
    <div className="catalogo-container">
      <h2>Catálogo</h2>
      
      <div style={{ backgroundColor: '#e6ffe6', padding: '15px', marginBottom: '20px', borderRadius: '5px' }}>
        <h3>Receba Promoções por E-mail</h3>
        <form onSubmit={assinarPromocoes}>
          <input 
            type="email" 
            placeholder="Seu e-mail" 
            value={email} 
            onChange={(e) => setEmail(e.target.value)} 
            required 
            style={{ padding: '5px', width: '250px', marginRight: '10px' }}
          />
          <div style={{ margin: '10px 0' }}>
            <label style={{ marginRight: '10px' }}>
              <input type="checkbox" name="papelaria" checked={categorias.papelaria} onChange={handleCategoriaChange} /> Papelaria
            </label>
            <label style={{ marginRight: '10px' }}>
              <input type="checkbox" name="escritorio" checked={categorias.escritorio} onChange={handleCategoriaChange} /> Escritório
            </label>
            <label>
              <input type="checkbox" name="acessorios" checked={categorias.acessorios} onChange={handleCategoriaChange} /> Acessórios
            </label>
          </div>
          <button type="submit" style={{ backgroundColor: '#28a745', color: 'white', border: 'none', padding: '8px 15px', borderRadius: '3px', cursor: 'pointer' }}>
            Inscrever-se
          </button>
        </form>
      </div>

      <div style={{ backgroundColor: '#f0f8ff', padding: '10px', marginBottom: '20px', borderRadius: '5px' }}>
        <h3>Status dos Pedidos:</h3>
        {notificacoes.length === 0 ? (
          <p>Nenhuma notificação por enquanto.</p>
        ) : (
          <ul>
            {notificacoes.map((notif, index) => (
              <li key={index} style={{ marginBottom: '10px' }}>
                Pedido #{notif.id_pedido} - Status atual: <strong>{notif.status}</strong>
                
                {notif.status !== 'pedido.excluido' && (
                  <button 
                    onClick={() => cancelarPedido(notif.id_pedido)} 
                    style={{ marginLeft: '15px', backgroundColor: '#ff4d4d', color: 'white', border: 'none', padding: '5px 10px', borderRadius: '3px', cursor: 'pointer' }}
                  >
                    Cancelar
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
      
      {produtos.map(produto => (
        <div key={produto.id_produto} className="card-produto" style={{ border: '1px solid #ccc', margin: '10px', padding: '10px' }}>
          <h3>{produto.nome}</h3>
          <p>R$ {produto.preco}</p>
          
          <input 
            type="number" 
            min="1" 
            value={quantidades[produto.id_produto] || 1} 
            onChange={(e) => handleQuantidadeChange(produto.id_produto, e.target.value)}
            style={{ width: '50px', marginRight: '10px', padding: '5px' }}
          />
          
          <button 
            onClick={() => comprarProduto(produto.id_produto)}
            style={{ padding: '5px 10px', cursor: 'pointer' }}
          >
            Comprar
          </button>
        </div>
      ))}
    </div>
  );
}

export default Catalogo;