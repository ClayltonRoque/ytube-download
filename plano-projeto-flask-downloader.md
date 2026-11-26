# Plano de desenvolvimento --- Media Downloader com Flask

## 1. Visão geral

Desenvolver uma aplicação web simples em Python para identificar
conteúdos do YouTube e realizar downloads usando `yt-dlp`.

A interface será uma **página única**, com foco em facilidade de uso:
inserir uma URL, identificar o conteúdo, escolher o tipo de mídia,
formato e qualidade, iniciar o download e acompanhar o progresso.

O projeto deve começar enxuto, mas organizado para permitir futuras
melhorias sem precisar reescrever toda a aplicação.

## 2. Definições já estabelecidas

  -----------------------------------------------------------------------
  Área                                Definição
  ----------------------------------- -----------------------------------
  Linguagem                           Python

  Backend                             Flask

  Frontend                            HTML com Jinja2, Tailwind CSS e
                                      JavaScript

  Interface                           Página única, simples e responsiva

  Motor de download                   `yt-dlp`

  Conversão e processamento           FFmpeg e FFprobe

  Integração Spotify                  Considerada como evolução;
                                      inicialmente consulta de metadados

  Banco de dados                      Não necessário na primeira versão

  Fila externa                        Não utilizar Celery/Redis no MVP

  Testes                              pytest

  Prioridade                          Refatorar e organizar a lógica de
                                      download existente, se possível
  -----------------------------------------------------------------------

### Decisões ainda não definidas

-   Se a aplicação será exclusivamente local ou se futuramente será
    publicada em um servidor.
-   Se o código atual será refatorado ou se o projeto será iniciado do
    zero reaproveitando a lógica existente.
-   Diretório padrão de destino dos arquivos.
-   Identidade visual definitiva.

Esses pontos não bloqueiam a primeira versão local.

## 3. Escopo do MVP

### 3.1 Funcionalidades essenciais

1.  Página inicial com campo para inserir URL.
2.  Identificação e validação do endereço informado.
3.  Consulta de metadados antes do download.
4.  Exibição de título, thumbnail, duração e informações disponíveis.
5.  Seleção do tipo de conteúdo:
    -   Áudio.
    -   Vídeo.
6.  Seleção de formato compatível.
7.  Seleção de qualidade disponível.
8.  Início do download com `yt-dlp`.
9.  Acompanhamento do progresso.
10. Mensagens de sucesso e erros compreensíveis.
11. Salvamento em diretório configurado pela aplicação.

### 3.2 Formatos e qualidade

**Áudio**

-   Formatos planejados: MP3, M4A, FLAC, WAV e Opus, conforme a
    disponibilidade e as opções de pós-processamento.
-   Qualidade: opções compatíveis com a fonte e com o formato escolhido.
-   Para MP3, permitir selecionar qualidade de conversão, por exemplo
    128, 192 ou 320 kbps.

**Vídeo**

-   Formato inicial preferencial: MP4.
-   Qualidade: apresentar somente resoluções disponíveis na fonte, como
    360p, 480p, 720p e 1080p.
-   Opção automática para selecionar a melhor qualidade compatível.

A interface não deve prometer uma qualidade que não exista na fonte. A
seleção final deve ser validada pelo backend.

## 4. Interface proposta

A aplicação terá uma única página, organizada em áreas:

### 4.1 Entrada

-   Campo de URL.
-   Ação para identificar o conteúdo.
-   Validação visual de URL inválida ou não suportada.

### 4.2 Prévia do conteúdo

Depois da identificação, apresentar:

-   Thumbnail.
-   Título.
-   Canal ou autor, quando disponível.
-   Duração, quando disponível.
-   Origem identificada.

### 4.3 Opções de download

-   Alternância entre áudio e vídeo.
-   Seletor de formato.
-   Seletor de qualidade.
-   Botão para iniciar o download.

As opções devem mudar conforme o tipo de mídia. Por exemplo, bitrate
para áudio e resolução para vídeo.

### 4.4 Progresso

Apresentar, quando disponíveis:

-   Percentual concluído.
-   Velocidade.
-   Tamanho transferido.
-   Estimativa de tempo restante.
-   Estado atual: aguardando, processando, concluído ou erro.

### 4.5 Estados da interface

A interface deve contemplar:

-   Estado inicial, sem URL.
-   Identificando conteúdo.
-   Conteúdo identificado.
-   Download em andamento.
-   Download concluído.
-   Erro de validação.
-   Erro durante o download.

## 5. Arquitetura e estrutura de diretórios

Estrutura inicial sugerida:

``` text
youtube-downloader/
├── app/
│   ├── __init__.py
│   ├── config.py
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   └── downloads.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── youtube.py
│   │   ├── downloader.py
│   │   └── spotify.py
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── validators.py
│   │   └── file_manager.py
│   │
│   ├── templates/
│   │   ├── base.html
│   │   └── index.html
│   │
│   └── static/
│       ├── css/
│       │   └── style.css
│       ├── js/
│       │   └── app.js
│       └── images/
│
├── downloads/
├── tests/
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
├── run.py
└── README.md
```

### Responsabilidades

  -----------------------------------------------------------------------
  Módulo                              Responsabilidade
  ----------------------------------- -----------------------------------
  `app/__init__.py`                   Application Factory e registro de
                                      rotas

  `app/config.py`                     Configurações da aplicação

  `routes/main.py`                    Renderizar a página principal

  `routes/downloads.py`               Endpoints de metadados, download,
                                      progresso e arquivo

  `services/youtube.py`               Consultar metadados e formatos
                                      disponíveis

  `services/downloader.py`            Configurar e executar o `yt-dlp`

  `services/spotify.py`               Consultar metadados do Spotify, em
                                      etapa futura

  `utils/validators.py`               Validar URLs e opções recebidas

  `utils/file_manager.py`             Gerenciar arquivos e diretórios de
                                      saída

  `templates/`                        Templates Jinja2

  `static/`                           CSS, JavaScript e imagens

  `tests/`                            Testes automatizados
  -----------------------------------------------------------------------

As rotas devem ser responsáveis por HTTP e validação de entrada. As
regras de negócio e a integração com `yt-dlp` devem permanecer nos
serviços.

## 6. Endpoints planejados

  -------------------------------------------------------------------------------
  Método                  Endpoint                        Responsabilidade
  ----------------------- ------------------------------- -----------------------
  `GET`                   `/`                             Renderizar a página
                                                          principal

  `POST`                  `/api/metadata`                 Consultar metadados e
                                                          formatos disponíveis

  `POST`                  `/api/download`                 Criar e iniciar um
                                                          download

  `GET`                   `/api/download/progress/<id>`   Consultar o progresso

  `GET`                   `/api/download/file/<id>`       Disponibilizar o
                                                          arquivo concluído
  -------------------------------------------------------------------------------

Os endpoints devem retornar respostas JSON consistentes, com indicação
clara de sucesso ou erro.

## 7. Fluxo técnico

### 7.1 Identificação

1.  O usuário informa uma URL.
2.  O frontend envia a URL para `/api/metadata`.
3.  O backend valida a URL e os protocolos permitidos.
4.  O serviço consulta o conteúdo com `yt-dlp`, sem iniciar o download.
5.  O backend retorna metadados e formatos disponíveis.
6.  O frontend apresenta a prévia e as opções de qualidade.

### 7.2 Download

1.  O usuário seleciona tipo, formato e qualidade.
2.  O frontend envia as opções para `/api/download`.
3.  O backend valida novamente todas as opções.
4.  A aplicação cria um identificador de tarefa.
5.  O download é executado em uma thread de trabalho, sem bloquear a
    requisição HTTP.
6.  Um `progress_hook` do `yt-dlp` atualiza o estado da tarefa.
7.  O frontend consulta `/api/download/progress/<id>` periodicamente.
8.  Ao concluir, o backend informa a disponibilidade do arquivo.

### 7.3 Concorrência e ciclo de vida

No MVP local, pode ser utilizada uma implementação simples em threads,
com:

-   Limite de downloads simultâneos.
-   Estado das tarefas mantido em memória.
-   Tratamento de exceções.
-   Timeout e possibilidade de cancelamento, se implementados com
    segurança.
-   Limpeza de tarefas antigas e arquivos temporários.

**Limitação:** tarefas e progresso mantidos em memória são perdidos
quando o processo reinicia. Essa abordagem é adequada apenas para a
primeira versão local e de uso limitado. Se houver necessidade de
persistência, múltiplos usuários ou execução em servidor, migrar para
uma fila de tarefas e armazenamento persistente.

## 8. Dependências

### Python --- MVP

``` txt
Flask
python-dotenv
yt-dlp
pytest
pytest-flask
```

`spotipy` será adicionado quando a integração de metadados do Spotify
for implementada.

### Dependências do sistema

-   Python 3.11 ou superior.
-   FFmpeg.
-   FFprobe.

No Ubuntu, FFmpeg pode ser instalado com:

``` bash
sudo apt update
sudo apt install ffmpeg
```

Verificar a instalação:

``` bash
python --version
ffmpeg -version
ffprobe -version
```

### Ferramentas de desenvolvimento

-   Ambiente virtual Python (`venv`).
-   Git.
-   Editor de código.
-   Navegador moderno.

## 9. Integração Spotify --- evolução futura

A integração Spotify não faz parte do fluxo essencial do MVP.

A proposta técnica é utilizar a Spotify Web API para consultar metadados
de músicas, artistas, álbuns e playlists, respeitando os mecanismos de
autorização e as políticas da plataforma.

Possíveis funcionalidades:

-   Informar uma URL de playlist ou álbum.
-   Consultar os metadados permitidos pela API.
-   Exibir faixas, artistas e capas.
-   Organizar uma coleção de músicas.
-   Apresentar links oficiais para reprodução e acesso ao conteúdo.

**Restrição importante:** a Spotify Web API não deve ser usada para
facilitar extração ou download não autorizado de áudio do Spotify. Não
implementar um fluxo que converta playlists do Spotify em downloads de
áudio de outra plataforma. Qualquer integração futura deve respeitar os
termos e direitos aplicáveis.

## 10. Segurança e confiabilidade

Mesmo em uma aplicação local, implementar cuidados básicos:

-   Aceitar somente URLs e protocolos esperados.
-   Validar os domínios e provedores suportados.
-   Nunca executar comandos montados com entrada do usuário usando
    `shell=True`.
-   Não permitir que o usuário determine caminhos arbitrários no
    servidor.
-   Gerar nomes de arquivos e identificadores de tarefa de forma segura.
-   Limitar tamanho, duração e quantidade de downloads simultâneos.
-   Tratar erros e timeouts do `yt-dlp`.
-   Manter credenciais em variáveis de ambiente.
-   Não versionar `.env`, downloads ou arquivos temporários.
-   Servir somente arquivos gerados pela própria aplicação e associados
    a tarefas válidas.

Se a aplicação for exposta à internet, será necessário adicionar
autenticação, autorização, rate limiting, limites de armazenamento,
isolamento de tarefas e controles adicionais contra SSRF e abuso de
recursos.

## 11. Testes

Criar testes para:

-   Validação de URLs aceitas e rejeitadas.
-   Consulta de metadados.
-   Seleção de formatos e qualidades.
-   Validação das opções de download.
-   Criação e atualização do estado da tarefa.
-   Tratamento de erros do `yt-dlp`.
-   Conclusão e disponibilização do arquivo.
-   Limpeza de arquivos temporários.

Os testes não devem depender de downloads reais em todas as execuções.
Utilizar mocks para testar a integração com `yt-dlp` de forma
previsível.

## 12. Etapas de implementação

### Fase 1 --- Fundação

-   [ ] Criar o repositório e o ambiente virtual.
-   [x] Criar a estrutura de diretórios.
-   [x] Configurar Flask com Application Factory.
-   [x] Registrar as rotas.
-   [x] Configurar variáveis de ambiente.
-   [ ] Criar a página inicial.
-   [ ] Verificar FFmpeg e FFprobe.

**Entrega:** aplicação Flask executando e renderizando a página
principal.

### Fase 2 --- Identificação do conteúdo

-   [ ] Implementar validação de URL.
-   [ ] Criar serviço de consulta com `yt-dlp`.
-   [ ] Implementar endpoint `/api/metadata`.
-   [ ] Retornar título, thumbnail, duração e formatos disponíveis.
-   [ ] Exibir a prévia no frontend.
-   [ ] Tratar URLs inválidas e erros do provedor.

**Entrega:** usuário consegue informar uma URL e visualizar os dados do
conteúdo.

### Fase 3 --- Download

-   [ ] Implementar serviço de download.
-   [ ] Configurar extração de áudio.
-   [ ] Configurar download de vídeo.
-   [ ] Implementar seleção de formato e qualidade.
-   [ ] Implementar execução em thread.
-   [ ] Implementar identificador e estado da tarefa.
-   [ ] Implementar `progress_hook`.
-   [ ] Criar endpoint de progresso.
-   [ ] Exibir progresso na interface.
-   [ ] Disponibilizar arquivo concluído.

**Entrega:** fluxo completo de download funcional.

### Fase 4 --- Interface e acabamento

-   [ ] Finalizar layout responsivo.
-   [ ] Implementar estados de carregamento.
-   [ ] Melhorar mensagens de erro.
-   [ ] Adicionar feedback de conclusão.
-   [ ] Melhorar acessibilidade e usabilidade.
-   [ ] Testar em diferentes navegadores.

**Entrega:** primeira versão utilizável e visualmente consistente.

### Fase 5 --- Melhorias futuras

-   [ ] Integração de metadados Spotify.
-   [ ] Suporte a playlists do YouTube, respeitando limites.
-   [ ] Histórico persistente.
-   [ ] Configurações de diretório e qualidade padrão.
-   [ ] Banco de dados, se necessário.
-   [ ] Fila persistente com Celery e Redis, se necessário.
-   [ ] Autenticação, caso seja disponibilizado para outros usuários.
-   [ ] Docker e deploy, caso o uso remoto seja decidido.

## 13. Critérios de conclusão do MVP

O MVP será considerado concluído quando:

-   [ ] A aplicação iniciar localmente sem erros.
-   [ ] A página principal for exibida corretamente.
-   [ ] Uma URL válida for identificada.
-   [ ] Os metadados forem exibidos.
-   [ ] O usuário conseguir escolher áudio ou vídeo.
-   [ ] Formato e qualidade forem validados pelo backend.
-   [ ] O download ocorrer sem bloquear a interface.
-   [ ] O progresso for atualizado na página.
-   [ ] O arquivo final for salvo no diretório configurado.
-   [ ] Erros forem apresentados de forma compreensível.
-   [ ] Os testes principais passarem.

## 14. Diretriz geral

Manter o projeto simples na primeira versão.

Não adicionar banco de dados, autenticação, Redis, Celery ou frontend
separado antes de existir uma necessidade concreta. Priorizar uma boa
separação entre rotas, serviços e interface, para que essas tecnologias
possam ser incorporadas futuramente sem comprometer a estrutura
existente.

**Ordem de prioridade:** aplicação Flask funcional → identificação de
conteúdo → download → progresso → acabamento visual → funcionalidades
adicionais.
