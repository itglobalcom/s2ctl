#!/bin/bash
# Публикация релиза s2ctl на GitHub: тег и бинарь становятся доступны
# по адресам из README (Installation). Запуск — job prod_release_github
# в .gitlab-ci.yml после сборки бинаря; аргумент — путь к архиву бинаря.
#
# Обязательное окружение: GITHUB_TOKEN (права contents:write на GITHUB_REPO),
# CI_COMMIT_TAG, CI_COMMIT_SHA. Необязательное: RELEASE_NOTES (иначе
# CI_COMMIT_TAG_MESSAGE), GITHUB_REPO, RELEASE_BRANCH, SOURCE_REMOTE,
# GITHUB_API, GITHUB_UPLOADS, GITHUB_REMOTE — последние три подменяются в тестах.
set -euo pipefail

ASSET_PATH="${1:?usage: release_github.sh <asset path>}"
: "${GITHUB_TOKEN:?GITHUB_TOKEN is required: a token with contents:write on the GitHub repository}"
: "${CI_COMMIT_TAG:?CI_COMMIT_TAG is required: the release tag}"
: "${CI_COMMIT_SHA:?CI_COMMIT_SHA is required: the tagged commit}"

GITHUB_REPO="${GITHUB_REPO:-itglobalcom/s2ctl}"
GITHUB_API="${GITHUB_API:-https://api.github.com}"
GITHUB_UPLOADS="${GITHUB_UPLOADS:-https://uploads.github.com}"
GITHUB_REMOTE="${GITHUB_REMOTE:-https://github.com/${GITHUB_REPO}.git}"
RELEASE_BRANCH="${RELEASE_BRANCH:-master}"
SOURCE_REMOTE="${SOURCE_REMOTE:-origin}"
RELEASE_NOTES="${RELEASE_NOTES:-${CI_COMMIT_TAG_MESSAGE:-}}"
ASSET_NAME=$(basename "$ASSET_PATH")

[[ -f "$ASSET_PATH" ]] || { echo "asset not found: $ASSET_PATH" >&2; exit 1; }

# Токен уходит в git заголовком, а не частью URL: URL печатается в сообщениях git.
GIT_AUTH_HEADER="Authorization: Basic $(printf 'x-access-token:%s' "$GITHUB_TOKEN" | base64 -w0)"
git_github() {
    git -c "http.extraHeader=$GIT_AUTH_HEADER" "$@"
}

api() {
    local method="$1" url="$2"
    shift 2
    curl --silent --show-error --fail-with-body \
        --request "$method" \
        --header "Authorization: Bearer $GITHUB_TOKEN" \
        --header "Accept: application/vnd.github+json" \
        --header "X-GitHub-Api-Version: 2022-11-28" \
        "$@" "$url"
}

json_field() {
    python3 -c 'import json, sys; print(json.load(sys.stdin)[sys.argv[1]])' "$1"
}

echo ">>> pushing tag $CI_COMMIT_TAG to $GITHUB_REPO"
git_github push "$GITHUB_REMOTE" "refs/tags/$CI_COMMIT_TAG:refs/tags/$CI_COMMIT_TAG"

echo ">>> looking up release $CI_COMMIT_TAG"
if release_json=$(api GET "$GITHUB_API/repos/$GITHUB_REPO/releases/tags/$CI_COMMIT_TAG" 2>/dev/null); then
    echo ">>> release exists, reusing it"
else
    echo ">>> creating release $CI_COMMIT_TAG"
    payload=$(TAG="$CI_COMMIT_TAG" SHA="$CI_COMMIT_SHA" NOTES="$RELEASE_NOTES" python3 -c '
import json, os
notes = os.environ["NOTES"].strip() or "s2ctl {tag}. Installation: see README.".format(tag=os.environ["TAG"])
print(json.dumps({
    "tag_name": os.environ["TAG"],
    "target_commitish": os.environ["SHA"],
    "name": os.environ["TAG"],
    "body": notes,
    "draft": False,
    "prerelease": False,
}))')
    release_json=$(api POST "$GITHUB_API/repos/$GITHUB_REPO/releases" --data "$payload")
fi
release_id=$(printf '%s' "$release_json" | json_field id)

# Повторный запуск job'а заменяет архив того же имени, а не падает на дубликате.
existing_asset_id=$(printf '%s' "$release_json" | ASSET_NAME="$ASSET_NAME" python3 -c '
import json, os, sys
assets = json.load(sys.stdin).get("assets", [])
print(next((asset["id"] for asset in assets if asset["name"] == os.environ["ASSET_NAME"]), ""))')
if [[ -n "$existing_asset_id" ]]; then
    echo ">>> replacing existing asset $ASSET_NAME"
    api DELETE "$GITHUB_API/repos/$GITHUB_REPO/releases/assets/$existing_asset_id"
fi

echo ">>> uploading $ASSET_NAME"
api POST "$GITHUB_UPLOADS/repos/$GITHUB_REPO/releases/$release_id/assets?name=$ASSET_NAME" \
    --header "Content-Type: application/gzip" \
    --data-binary "@$ASSET_PATH" > /dev/null

# GitHub — зеркало публикации: его ветка релиза повторяет ветку релиза GitLab,
# если выпущенный коммит лежит на ней.
git fetch --quiet "$SOURCE_REMOTE" "+refs/heads/$RELEASE_BRANCH:refs/remotes/$SOURCE_REMOTE/$RELEASE_BRANCH"
if git merge-base --is-ancestor "$CI_COMMIT_SHA" "refs/remotes/$SOURCE_REMOTE/$RELEASE_BRANCH"; then
    echo ">>> syncing $RELEASE_BRANCH to $GITHUB_REPO"
    git_github push --force "$GITHUB_REMOTE" "$CI_COMMIT_SHA:refs/heads/$RELEASE_BRANCH"
else
    echo ">>> $CI_COMMIT_TAG is not on $RELEASE_BRANCH, branch left as is"
fi

echo ">>> released $CI_COMMIT_TAG: https://github.com/$GITHUB_REPO/releases/tag/$CI_COMMIT_TAG"
