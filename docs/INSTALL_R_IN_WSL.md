# Install R in WSL (for VS Code / Cursor Remote - WSL)

**Short answer:** Install R **inside WSL**. Do **not** use Windows R or Wine. When you run VS Code/Cursor in WSL (Remote - WSL), the editor runs on Windows but the terminal and all commands (including R) run in Linux, so R must be the Linux version in your WSL distro.

---

## 1. Install R inside WSL

Open a WSL terminal (e.g. Ubuntu) and run one of the following.

### Option A: Ubuntu package (quick, may be older R)

```bash
sudo apt update
sudo apt install -y r-base
```

### Option B: CRAN repository (newer R, recommended for Ubuntu 22.04+)

```bash
sudo apt update -qq
sudo apt install -y --no-install-recommends software-properties-common dirmngr
wget -qO- https://cloud.r-project.org/bin/linux/ubuntu/marutter_pubkey.asc | sudo tee -a /etc/apt/trusted.gpg.d/cran_ubuntu_key.asc
sudo add-apt-repository "deb https://cloud.r-project.org/bin/linux/ubuntu $(lsb_release -cs)-cran40/"
sudo apt update
sudo apt install -y --no-install-recommends r-base
```

### Optional: dependencies for common R packages

Reduces install failures for packages that need system libs:

```bash
sudo apt-get install -y libxml2-dev libcurl4-openssl-dev libssl-dev gfortran liblapack-dev libopenblas-dev
# If you need graphics/fonts (e.g. for httpgd, ggplot2):
sudo apt install -y libfontconfig1-dev libharfbuzz-dev libfribidi-dev libfreetype6-dev libpng-dev libtiff5-dev libjpeg-dev
```

### Verify

```bash
R --version
```

Or start R and run `version` inside the session.

---

## 2. R packages for the VS Code R extension (run inside R in WSL)

The **R extension** (REditorSupport.r) works best with these R packages installed. In WSL, start R (`R`) and run:

```r
# Essential: language server (completion, hover, go-to-definition, diagnostics)
install.packages("languageserver")

# Recommended: plot viewer in VS Code, linting
install.packages("httpgd")   # Interactive plots in the editor
install.packages("lintr")    # Code linting (warnings, style)

# Optional: nicer help display in hover
install.packages("rmarkdown")
```

| Package         | Purpose |
|----------------|--------|
| **languageserver** | Required for IntelliSense, completion, hover docs, diagnostics. |
| **httpgd**     | Lets the R extension show plots inside VS Code (like RStudio’s plot pane). |
| **lintr**      | Powers linting (warnings and style in the editor). |
| **rmarkdown**  | Optional; improves formatted help in hover. |

### What about “r-essentials”?

**r-essentials** is a **Conda** meta-package (not something you install from inside R with `install.packages()`). It bundles a set of common R packages (e.g. for data science). You only need it if you install and use R **via Conda** in WSL:

```bash
# Only if you use conda for R (optional alternative to apt/CRAN)
conda install -c conda-forge r-essentials
```

- If you installed R with **apt** or the **CRAN repo** (as in section 1 above), use the R packages in the table above. There is no separate “r.essential” R package for the VS Code extension.
- If you **do** use a conda R environment, `r-essentials` can give you a batch of packages at once; the VS Code R extension still needs **languageserver** (and optionally **httpgd**, **lintr**) inside that same environment.

**Packages included in r-essentials** (conda-forge recipe). In plain R you'd install these from CRAN with `install.packages("name")`:

| R package (CRAN name) | Typical use |
|------------------------|-------------|
| **r-base** + **r-recommended** | R core + recommended bundles |
| **ggplot2** | Plotting |
| **plyr**, **reshape2** | Data reshaping |
| **dplyr**, **tidyr** | Data manipulation (tidyverse core) |
| **tidyverse** (meta) | dplyr, tidyr, readr, purrr, tibble, stringr, forcats, etc. |
| **readr**, **readxl**, **haven** | Read CSV, Excel, Stata/SAS/SPSS |
| **lubridate**, **hms** | Dates and times |
| **stringr** | Strings |
| **tibble**, **purrr**, **magrittr** | Data structures and piping |
| **httr**, **rvest**, **xml2** | Web and APIs |
| **rmarkdown** | R Markdown docs |
| **shiny** | Web apps |
| **caret**, **randomForest**, **glmnet** | ML / modeling |
| **data.table** | Fast data tables |
| **quantmod** | Quantitative finance |
| **jsonlite**, **zoo** | JSON, time series |
| **broom** | Tidy model output |
| **DBI** | Database interface |
| **irkernel** | Jupyter R kernel |
| **formatR** | Code formatting |

---

## 3. VS Code / Cursor with WSL

1. **On Windows:** Install [Remote - WSL](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-wsl).
2. **Connect to WSL:** From Windows, `Ctrl+Shift+P` → “WSL: Connect to WSL” or “WSL: New Window”; or from WSL terminal run `code .` (or `cursor .`) in your project folder.
3. **Install R extension in WSL:** With the window connected to WSL, open Extensions, search for **R** (REditorSupport.r), install. The extension runs in the WSL context and will use the R you installed in WSL.
4. **Optional (radian):** In WSL: `pip install -U radian` (or `pip3`). Configure the R extension to use `radian` as the R terminal if you want.

No path configuration is usually needed: the R extension detects R in the WSL PATH. If it doesn’t, set in VS Code (WSL) settings:

- `r.rpath.linux`: e.g. `/usr/bin/R` or `which R` in WSL.

---

## 4. Why WSL, not Windows or Wine?

| Where R runs        | When it makes sense |
|---------------------|----------------------|
| **Inside WSL**      | You use VS Code “in WSL” (Remote - WSL). Terminal and R must be the Linux R in WSL. **Use this.** |
| Windows (native)    | You use VS Code on Windows only and run R in a Windows terminal. Different environment from WSL. |
| Wine (Windows R in WSL) | Unnecessary and more fragile. You’d run Windows R inside Linux; the extension and terminal expect Linux R. **Don’t do this.** |

**Summary:** If you’re running VS Code in WSL, install and use R **inside that same WSL environment**.
