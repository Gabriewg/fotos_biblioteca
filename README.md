# Fotos Organizer

Um organizador local de fotos, no estilo do aplicativo **Fotos** do Apple/Android, que lê a **data de captura (EXIF)** de cada imagem e a organiza automaticamente por data — **sem depender de nenhum serviço na nuvem**. Tudo fica no seu HD.

## Funcionalidades

- 📅 **Organização por data real**: lê a data de captura do EXIF (`DateTimeOriginal`, com fallback para `DateTime`) e organiza em `output/ANO/MM-DD/`.
- 🕓 **Fallback inteligente**: fotos sem EXIF são organizadas pela **data de modificação do arquivo**; fotos sem nenhuma das duas são ignoradas com aviso.
- 🧪 **Dry-run por padrão**: simula exatamente o que seria feito, **sem tocar em nenhum arquivo**. Só copia de verdade com `--no-dry-run`.
- 🏷️ **Renomear com a data**: opcionalmente renomeia os arquivos copiados (ex.: `2026-08-13_19-14-02_IMG_1422.jpg`).
- 🔁 **Detecção de duplicadas**: encontra fotos repetidas por **hash de conteúdo (MD5)** e mantém apenas a primeira de cada grupo.
- 🖥️ **Interface gráfica (GUI)**: janela estilo aplicativo Fotos com prévias, filtro por data, agrupamento por mês e visualização em tamanho grande.
- 📱 **HEIC/HEIF**: suporte a fotos de iPhone (`pillow-heif`).
- 🛡️ **Tolerante a erros**: imagens truncadas/corrompidas não quebram a execução.
- 🔒 **Seguro**: o programa **nunca move nem apaga suas fotos originais** — a única ação de escrita é copiar para a pasta de destino.
- 🔂 **Instância única**: apenas uma janela abre por vez; tentar abrir de novo foca na existente.

## Como funciona

1. O programa percorre as pastas/arquivos de origem informados.
2. Para cada foto, lê o EXIF e extrai a data original (tag `DateTimeOriginal` da **Exif SubIFD**, com fallback para `DateTime`). Se não houver EXIF, usa a **data de modificação do arquivo** como fallback.
3. Calcula o destino: `output/ANO/MM-DD/` (ex.: `output/2026/08-13/`).
4. Copia a foto para o destino, resolvendo conflitos de nome (`_1`, `_2`, ...).
5. Fotos sem data no EXIF e sem data de modificação acessível são ignoradas (com aviso).

> Por padrão o programa roda em **modo dry-run**: ele mostra exatamente o que seria feito, **sem tocar em nenhum arquivo**. Só copia de verdade com `--no-dry-run`.

## Bugs corrigidos

Durante o desenvolvimento, alguns bugs foram encontrados e corrigidos:

- **EXIF `DateTimeOriginal` não era lido na maioria das câmeras** — a tag `DateTimeOriginal` fica na **Exif SubIFD**, não na raiz do bloco EXIF (IFD0). `image.getexif()[36867]` retornava `None` para muitas fotos, que acabavam sendo organizadas pela data de modificação do arquivo. A correção lê a SubIFD via `exif.get_ifd(ExifTags.IFD.Exif)` e prioriza `DateTimeOriginal`, com fallback para `DateTime`. `src/metadata.py`
- **Fotos de exemplo gigantes no repositório** — as fotos reais de teste (vários MB cada) foram removidas do histórico. Em seu lugar foram adicionadas **fotos sintéticas de exemplo** (poucos KB) em `sample_photos/`, mantendo a cobertura de testes.
- **Testes que falhavam dependendo do dia da execução** — os testes de organização usavam a data de modificação dos arquivos de exemplo, o que quebrava em clones feitos em dias diferentes. Os testes foram tornados **independentes do mtime**, funcionando em qualquer data.

## Estrutura

```
├── src/
│   ├── metadata.py      # Extração da data do EXIF (com fallback p/ data do arquivo)
│   ├── organizer.py     # Lógica de organização (dry-run, cópia e renomeação)
│   ├── duplicates.py    # Detecção de duplicadas (hash de conteúdo)
│   ├── cli.py           # Interface de linha de comando (Typer)
│   └── gui.py           # Interface gráfica (PySide6/Qt)
├── tests/
│   ├── test_metadata.py
│   ├── test_organizer.py
│   └── test_duplicates.py
├── sample_photos/       # Fotos sintéticas de exemplo para testes
├── output/              # Destino das fotos organizadas (gitignored)
├── main.py              # Entry point da CLI
├── main_gui.pyw         # Entry point da interface gráfica (sem console)
├── FotosOrganizer.spec  # Spec do PyInstaller
├── LICENSE              # Licença MIT
├── requirements.txt
└── .gitignore
```

## Como rodar

### Requisitos

- Python 3.10+
- Windows, macOS ou Linux

### Instalação

```bash
python -m venv .venv
.\.venv\Scripts\activate   # Windows (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
```

### Interface gráfica

```bash
python main_gui.py
```

Para abrir **sem janela de terminal** (Windows), use o arquivo `.pyw`:

```bash
pythonw main_gui.pyw
```

Ou simplesmente dê dois cliques em `main_gui.pyw`.

Na janela:

1. **＋ Adicionar fotos** ou **＋ Adicionar pasta** para escolher as imagens (só listagem/visualização — não move nada do HD).
2. Use o campo **Filtrar por data** (ex.: `2026`, `2026-08` ou `08/2026`) para navegar rápido.
3. Escolha a **pasta de destino** (padrão: `output/`).
4. Marque/desmarque **Simular (dry-run)** e, se quiser, **Renomear com a data**.
5. Clique em **Organizar** — em dry-run mostra o plano; desmarque dry-run para copiar de verdade. Depois de organizar, um botão **✕** aparece ao lado para voltar à visualização normal.
6. **Detectar duplicadas** encontra fotos repetidas (por conteúdo) e pergunta se quer removê-las da lista.
7. Duplo clique em uma foto para visualizar em tamanho grande; use `←`/`→` para navegar, `Esc` para fechar e **Abrir local do arquivo** para ver a pasta no Explorer.
   As fotos aparecem agrupadas por mês. Para selecionar várias, use Ctrl/Shift e depois **Remover selecionadas**.

### Interface de linha de comando

Organizar todas as fotos de uma pasta:

```bash
python main.py CAMINHO/DA/PASTA
```

Organizar vários arquivos/pastas de uma vez:

```bash
python main.py pasta1 pasta2 foto_solta.jpg
```

#### Opções

| Opção | Descrição |
|---|---|
| `-o, --output PASTA` | Pasta de destino (padrão: `output/`) |
| `--no-dry-run` | Copia as fotos de verdade (padrão é apenas simular) |
| `--rename` | Renomeia as fotos copiadas com a data no nome |
| `--help` | Mostra a ajuda completa |

#### Exemplos

Simular sem alterar nada:

```bash
python main.py ~/Pictures
```

Copiar de verdade para `organizadas/`:

```bash
python main.py ~/Pictures -o organizadas --no-dry-run
```

### Executável (Windows)

Basta executar `dist\FotosOrganizer.exe` — não precisa de Python instalado. Para gerar de novo:

```bash
.\.venv\Scripts\pyinstaller.exe --noconfirm --noconsole --onefile --name FotosOrganizer --collect-all pillow_heif --collect-submodules pillow_heif main_gui.pyw
```

### Testes

```bash
python -m pytest tests -v
```

Os testes usam as fotos sintéticas em `sample_photos/`.

## Licença

MIT — veja o arquivo [LICENSE](LICENSE).