# Twitter Video

Ferramenta local para baixar vídeos de posts públicos do X/Twitter que você tem permissão para salvar. Ela não usa uma API paga, login, cookies, tokens nem contorna conteúdo privado ou controles de acesso.

## Instalação no usuário atual

Abra o PowerShell nesta pasta e execute:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

O instalador cria um ambiente isolado em `%USERPROFILE%\.local\TwitterVideo`, cria o comando `twitter-video` e altera somente o PATH do seu usuário. Não pede administrador, não escreve em `Program Files` e não muda configurações de outros usuários.

Feche e abra um novo PowerShell depois da instalação para que o comando fique disponível. Confirme com:

```powershell
twitter-video --version
```

O instalador usa uma instalação funcional de Python do seu usuário. Se `python` estiver apontando apenas para o atalho da Microsoft Store, ele também procura o Python local gerenciado pelo `uv`. Caso nenhum dos dois esteja disponível, ele mostra como instalar o Python para o usuário atual.

## Baixar um post

```powershell
twitter-video https://x.com/jobecoffe/status/2108403966665199628
```

Todos os vídeos nativos que o `yt-dlp` conseguir acessar naquele post são salvos em:

```text
%USERPROFILE%\Downloads\Twitter_Videos
```

Use a URL simples do post, terminada em `/status/<id>`; não use o sufixo
`/video/<n>`, que selecionaria apenas um vídeo. Links externos incorporados no
post não são seguidos. Um arquivo com o mesmo nome já existente não é sobrescrito
e aparece como `Skipped` no resumo.

## Baixar vários posts de uma thread

Na versão sem custo, a ferramenta não tenta descobrir automaticamente os próximos posts da thread. Crie um arquivo UTF-8, por exemplo `thread.txt`, com uma URL pública por linha:

```text
# Minha thread
https://x.com/autor/status/111
https://x.com/autor/status/222
https://x.com/autor/status/333
```

Então execute:

```powershell
twitter-video --file .\thread.txt
```

Linhas em branco e linhas iniciadas por `#` são ignoradas. Uma URL inválida ou indisponível é informada, mas as outras URLs válidas continuam sendo processadas.

## ffmpeg

Para juntar vídeo e áudio na melhor qualidade, é necessário ter `ffmpeg` disponível no PATH. Se ele estiver ausente, o comando mostra uma mensagem antes de começar o download. Instale o `ffmpeg`, abra um novo PowerShell e repita o comando.

## Limitações e resolução de problemas

- Posts privados, removidos, protegidos, com bloqueio regional ou sem vídeo não podem ser baixados.
- O X pode alterar sua forma de disponibilizar mídia pública. Quando isso acontecer, atualize a dependência com `& "$env:USERPROFILE\.local\TwitterVideo\venv\Scripts\python.exe" -m pip install --upgrade yt-dlp` ou execute novamente `install.ps1` após atualizar este projeto.
- A ferramenta não processa conteúdo que exige login, cookies ou qualquer contorno de controles de acesso.
