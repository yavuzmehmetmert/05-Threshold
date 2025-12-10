#!/bin/bash
current_limit=$(ulimit -n)
echo "Mevcut limit: $current_limit"

if [ "$current_limit" != "unlimited" ] && [ "$current_limit" -lt 10240 ]; then
    echo "Dosya limitleri artırılıyor (10240)..."
    ulimit -n 10240
else
    echo "Limit yeterli, değiştirilmiyor."
fi

echo "Expo başlatılıyor..."
npx expo start
