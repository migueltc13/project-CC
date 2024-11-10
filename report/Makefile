# LaTeX Engine
TEX = xelatex
FLAGS = -output-directory=$(OUTPUT_DIR) -shell-restricted

# Output directory
OUTPUT_DIR = output

# Main LaTeX file
FILE_NAME = main

# Font name
FONT_NAME = Arial

.PHONY: all dir index compile install clean

all: dir compile

dir:
	mkdir -p $(OUTPUT_DIR)

index:
	# Dynamically handle .nlo files for indexing
	find $(OUTPUT_DIR) -name "*.nlo" -exec makeindex {} -s nomencl.ist -o {}.nls \; \
		|| echo "No .nlo files found. Skipping indexing."

compile: index
	$(TEX) $(FLAGS) $(FILE_NAME).tex

install:
	# Install the required packages
	sudo apt update
	sudo apt install \
		texlive-xetex \
		texlive-lang-portuguese \
		texlive-latex-recommended \
		ttf-mscorefonts-installer \
		texlive-fonts-extra \
		fonts-stix
	# Check if font is installed
	sudo fc-cache -f && fc-match $(FONT_NAME) \
		|| echo "$(FONT_NAME) font not found"

clean:
	rm -rf $(OUTPUT_DIR)
