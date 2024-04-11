#!/bin/bash
#
# lingua is required
#
# Usage:
#     Initial catalog creation (lang is the language identifier):
#         ./i18n.sh lang
#     Updating translation and compile catalog:
#         ./i18n.sh

# configuration
DOMAIN="privatim"
SEARCH_PATH="src/privatim"
LOCALES_PATH="src/privatim/locale"
# end configuration


# Check if lingua is installed
if ! command -v pot-create &> /dev/null
then
    echo "lingua is not installed. Please install it (pip install lingua) before continuing."
    exit 1
fi

# create locales folder if not exists
if [ ! -d "$LOCALES_PATH" ]; then
    echo "Locales directory not exists, create"
    mkdir -p "$LOCALES_PATH"
fi

# create pot if not exists
if [ ! -f "$LOCALES_PATH"/$DOMAIN.pot ]; then
    echo "Create pot file"
    touch "$LOCALES_PATH"/$DOMAIN.pot
fi

# no arguments, extract and update
if [ $# -eq 0 ]; then
    echo "Extract messages"
    pot-create --no-linenumbers "$SEARCH_PATH" -o "$LOCALES_PATH"/$DOMAIN.pot

    echo "Update translations"
    for po in "$LOCALES_PATH"/*/LC_MESSAGES/$DOMAIN.po; do
        msgmerge --no-fuzzy-matching -o "$po" "$po" "$LOCALES_PATH"/$DOMAIN.pot
    done

    echo "Compile message catalogs"
    for po in "$LOCALES_PATH"/*/LC_MESSAGES/*.po; do
        msgfmt --statistics -o "${po%.*}.mo" "$po"
    done

# first argument represents language identifier, create catalog
else
    cd "$LOCALES_PATH"
    mkdir -p $1/LC_MESSAGES
    msginit -i $DOMAIN.pot -o $1/LC_MESSAGES/$DOMAIN.po -l $1
fi
