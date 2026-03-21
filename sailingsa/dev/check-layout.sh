#!/bin/bash

FILES=$(git diff --name-only HEAD)

for file in $FILES
do
    if [[ "$file" == *"frontend/"* ]] && [[ "$file" == *".html" ]]; then
        [[ ! -f "$file" ]] && continue
        # Skip auth/popup/minimal pages that don't use card layout
        base=$(basename "$file")
        [[ "$base" == "login.html" ]] || [[ "$base" == "popup.html" ]] || [[ "$base" == "facebook-confirm.html" ]] && continue

        if ! grep -qE 'class="[^"]*container' "$file"; then
            echo "Layout error: container missing in $file"
            exit 1
        fi

        if ! grep -q 'class="card' "$file"; then
            echo "Layout error: card component missing in $file"
            exit 1
        fi

    fi
done

echo "Layout check passed."
