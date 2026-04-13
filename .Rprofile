# pyrbmi local R development setup
# This file configures R to use binary packages via Posit Package Manager
# eliminating source compilation (same 5-10 sec install as r2u in CI)

# Detect OS and set appropriate binary mirror
if (Sys.info()["sysname"] == "Linux") {
  # Detect distro for correct binary URL
  distro <- tryCatch({
    lines <- readLines("/etc/os-release")
    id_line <- grep("^ID=", lines, value = TRUE)
    gsub('ID="?', "", id_line)
  }, error = function(e) "ubuntu")
  
  # Map distro to PPM codename
  codename <- switch(distro,
    "ubuntu" = "noble",    # 24.04
    "debian" = "bookworm", # 12
    "fedora" = "fc40",
    "noble"  # default
  )
  
  options(repos = c(
    CRAN = paste0("https://packagemanager.posit.co/cran/__linux__/, codename, /latest"),
    PPM = "https://packagemanager.posit.co/cran/latest"
  ))
  
  message(sprintf("Using Posit Package Manager binary mirror for %s (%s)", distro, codename))
  
} else if (Sys.info()["sysname"] == "Darwin") {
  # macOS - use PPM but no binaries available, use CRAN
  options(repos = c(CRAN = "https://cloud.r-project.org"))
  message("Using CRAN (macOS binaries from CRAN)")
  
} else if (Sys.info()["sysname"] == "Windows") {
  # Windows - use PPM or CRAN (both have binaries)
  options(repos = c(CRAN = "https://packagemanager.posit.co/cran/latest"))
  message("Using Posit Package Manager (Windows binaries)")
}

# Prevent source compilation where possible
options(install.packages.compile.from.source = "never")

# Parallel installation for faster package installs
options(Ncpus = max(1, parallel::detectCores() - 1))

# Confirm rpy2 can find R (useful for debugging)
if (requireNamespace("rstudioapi", quietly = TRUE) || interactive()) {
  message("R home: ", R.home())
  message("R version: ", getRversion())
}

# Optional: auto-load devtools if installed
if (requireNamespace("devtools", quietly = TRUE)) {
  suppressPackageStartupMessages(library(devtools))
}
