# AutoPro Garage — demonstração de sistema de oficina

## O que está incluído
- Site público responsivo com seções Início, Serviços, Sobre, Dicas e Contato.
- Formulário público de solicitação de agendamento.
- Área administrativa com login demonstrativo.
- Cadastro, edição, pesquisa e exclusão de clientes e veículos.
- Gestão de agendamentos com atualização de status.
- Orçamentos com valores de peças e mão de obra, status e criação de ordem de serviço.
- Ordens de serviço com fluxo de status.
- Lançamentos financeiros de entradas e saídas.
- Persistência de demonstração usando `localStorage` no navegador.

## Como executar
1. Extraia o ZIP.
2. Abra `index.html` em um navegador atualizado. Para melhores resultados, use VS Code com a extensão Live Server.
3. Clique em **Área administrativa** no rodapé.
4. Use o acesso demonstrativo:
   - E-mail: `admin@autopro.local`
   - Senha: `admin123`

## Limitações importantes
Este projeto é um protótipo frontend. HTML, CSS e JavaScript no navegador não fornecem autenticação segura nem um banco de dados centralizado. Os dados ficam no navegador atual, podem ser apagados pelo usuário e não são compartilhados entre computadores. A senha demonstrativa está no código e não deve ser usada em produção.

Para transformar em um sistema real, é necessário acrescentar backend (por exemplo, PHP ou Node.js), banco de dados (MySQL ou equivalente), senhas armazenadas com hash no servidor, controle de sessão, validação no servidor, proteção CSRF, autorização por perfil, backups e configuração HTTPS. Também é necessário configurar dados reais da oficina, WhatsApp, endereço e avaliações verificadas.

As imagens de capa vêm de URLs externas do Unsplash e precisam de conexão à internet. A identidade AutoPro e os registros são ilustrativos.
