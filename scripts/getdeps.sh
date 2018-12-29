curl https://api.github.com/repos/rxi/json.lua/contents/json.lua?ref=v0.1.1 | jq -r '.content' | base64 --decode > json.lua
curl https://api.github.com/repos/kikito/inspect.lua/contents/inspect.lua?ref=v3.1.1 | jq -r '.content' | base64 --decode > inspect.lua
curl https://api.github.com/repos/guysv/netstring.lua/contents/netstring.lua?ref=v0.1.0 | jq -r '.content' | base64 --decode > netstring.lua