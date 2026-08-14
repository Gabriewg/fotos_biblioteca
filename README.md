# Fotos Organizer

Um organizador local de fotos, no estilo do aplicativo **Fotos** do Apple/Android, que lê a **data de captura (EXIF)** de cada imagem e a organiza automaticamente por data — sem depender de nenhum serviço na nuvem.

## Como funciona

1. O programa percorre as pastas/arquivos de origem informados.
2. Para cada foto, lê o EXIF e extrai a data original (tag `DateTimeOriginal`, com fallback para `DateTime`). Se não houver EXIF, usa a **data de modificação do arquivo** como fallback.
3. Calcula o destino: `output/ANO/MM-DD/` (ex.: `output/2026/08-13/`).
4. Copia a foto para o destino, resolvendo conflitos de nome (`_1`, `_2`, ...).
5. Fotos sem data no EXIF e sem data de modificação acessível são ignoradas (com aviso).

> Por padrão o programa roda em **modo dry-run**: ele mostra exatamente o que seria feito, **sem tocar em nenhum arquivo**. Só copia de verdade com `--no-dry-run`.

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
├── sample_photos/       # Fotos reais de exemplo para testes
├── output/              # Destino das fotos organizadas (gitignored)
├── main.py              # Entry point da CLI
├── main_gui.pyw         # Entry point da interface gráfica (sem console)
├── dist/                # Executável gerado (FotosOrganizer.exe)
├── requirements.txt
└── .gitignore
```

## Instalação

```bash
python -m venv .venv
.\.venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

## Uso

Organizar todas as fotos de uma pasta:

```bash
python main.py CAMINHO/DA/PASTA
```

Organizar vários arquivos/pastas de uma vez:

```bash
python main.py pasta1 pasta2 foto_solta.jpg
```

### Opções

| Opção | Descrição |
|---|---|
| `-o, --output PASTA` | Pasta de destino (padrão: `output/`) |
| `--no-dry-run` | Copia as fotos de verdade (padrão é apenas simular) |
| `--rename` | Renomeia as fotos copiadas com a data no nome |
| `--help` | Mostra a ajuda completa |

### Exemplos

Simular sem alterar nada:

```bash
python main.py ~/Pictures
```

Copiar de verdade para `organizadas/`:

```bash
python main.py ~/Pictures -o organizadas --no-dry-run
```

## Interface gráfica

Uma janela estilo aplicativo Fotos (PySide6) com prévias das fotos.

Para abrir **sem janela de terminal** (Windows), use o arquivo `.pyw`:

```bash
pythonw main_gui.pyw
```

Ou simplesmente dê dois cliques em `main_gui.pyw`.

### Executável (Windows)

Basta executar `dist\FotosOrganizer.exe` — não precisa de Python instalado. Para gerar de novo:

```bash
.\.venv\Scripts\pyinstaller.exe --noconfirm --noconsole --onefile --name FotosOrganizer --collect-all pillow_heif --collect-submodules pillow_heif main_gui.pyw
```

Na janela:

1. **Adicionar fotos** ou **Adicionar pasta** para escolher as imagens (só listagem/visualização — não move nada do HD).
2. Use o campo **Filtrar por data** (ex.: `2026`, `2026-08` ou `08/2026`) para navegar rápido.
3. Escolha a **pasta de destino** (padrão: `output/`).
4. Marque/desmarque **Simular (dry-run)** e, se quiser, **Renomear com a data** (nome fica `2026-08-13_19-14-02_IMG_1422.jpg`).
5. Clique em **Organizar** — em dry-run mostra o plano; desmarque dry-run para copiar de verdade. Depois de organizar, um botão **✕** aparece ao lado para voltar à visualização normal.
6. **Detectar duplicadas** encontra fotos repetidas (por conteúdo) e pergunta se quer removê-las da lista.
7. Duplo clique em uma foto para visualizar em tamanho grande; use `←`/`→` para navegar, `Esc` para fechar e **Abrir local do arquivo** para ver a pasta no Explorer.
   As fotos aparecem agrupadas por mês. Para selecionar várias, use Ctrl/Shift e depois **Remover selecionadas**.

> Nota: o programa **nunca move nem apaga suas fotos originais**. As pastas adicionadas são
> apenas para visualização. A única ação que cria arquivos é clicar em **Organizar** com
> **Simular (dry-run)** desmarcado, que **copia** as fotos para a pasta de destino.
>
> Suporta **HEIC/HEIF** (iPhone) e imagens truncadas/corrompidas. Apenas **uma janela** abre por
> vez — tentar abrir de novo foca na janela existente.

## Testes

```bash
python -m pytest tests -v
```

Os testes usam as fotos reais em `sample_photos/`.

## Próximos passos planejados

- [x] Tratar fotos sem EXIF usando a data de modificação do arquivo como fallback
- [x] Interface gráfica desktop (PySide6) com prévias e organização por clique
- [x] Remover duplicadas (hash de conteúdo)
- [ ] Concorrência (multiprocessing) para fotos em massa
- [ ] Lembrar as pastas adicionadas e reabrir a lista na próxima execução
