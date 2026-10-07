import { useState, useEffect } from 'react';

function Catalogo() {
  const [produtos, setProdutos] = useState([]);
  const [notificacoes, setNotificacoes] = useState([]);

  useEffect(() => {
    // busca a lista de produtos no ms_principal (API Gateway)
    fetch('http://localhost:5000/produtos')
      .then(res => res.json())
      .then(dados => setProdutos(dados))
      .catch(erro => console.error("erro ao carregar produtos:", erro));
  }, []);

  useEffect(() => {
    const eventSource = new EventSource('http://localhost:5000/stream');

    eventSource.onmessage = (event) => {
      const novaNotificacao = JSON.parse(event.data);

      setNotificacoes((notificacoesAnteriores) => [
        ...notificacoesAnteriores,
        novaNotificacao
      ]);
    };

    return () => eventSource.close();
  }, []);

  const comprarProduto = (id_produto) => {
    // On envoie une requête POST au MS Principal
    fetch('http://localhost:5000/comprar', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      // On envoie les données de la commande en format JSON
      body: JSON.stringify({ 
        id_produto: id_produto, 
        quantidade: 1, 
        cliente: "Imane" 
      })
    })
    .then(res => res.json())
    .then(dados => {
      console.log(dados);
    })
    .catch(erro => console.error("Erro ao comprar produto:", erro));
  };

  return (
    <div className="catalogo-container">
      <h2>Catálogo</h2>
      <div style={{ backgroundColor: '#f0f8ff', padding: '10px', marginBottom: '20px', borderRadius: '5px' }}>
        <h3>Status dos Pedidos:</h3>
        {notificacoes.length === 0 ? (
          <p>Nenhuma notificação por enquanto.</p>
        ) : (
          <ul>
            {notificacoes.map((notif, index) => (
              <li key={index}>
                Pedido #{notif.id_pedido} - Status atual: <strong>{notif.status}</strong>
              </li>
            ))}
          </ul>
        )}
      </div>
      {produtos.map(produto => (
        <div key={produto.id_produto} className="card-produto" style={{ border: '1px solid #ccc', margin: '10px', padding: '10px' }}>
          <h3>{produto.nome}</h3>
          <p>R$ {produto.preco}</p>
          <button onClick={() => comprarProduto(produto.id_produto)}>Comprar</button>
        </div>
      ))}
    </div>
  );
}

export default Catalogo;