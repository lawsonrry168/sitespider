#!/usr/bin/env bash
# 複製為 gsc-env.sh 並填入本機 client_secret 路徑（勿 commit 真實路徑）
# 使用：source scripts/gsc-env.sh

export GSC_OAUTH_CLIENT_JSON="${GSC_OAUTH_CLIENT_JSON:-$HOME/.secrets/gsc-oauth-client.json}"
export GSC_OAUTH_TOKEN_PATH="${GSC_OAUTH_TOKEN_PATH:-$HOME/.config/sitespider/gsc-oauth-token.json}"
