# Lydia - Quickstart

### Basic Setup

To get started using this tool, you need to set some base parameters. Set these variables (if you are using another provider, just name the relevant variables OPENAI anyway):

```
export OPENAI_BASE_URL=
export OPENAI_API_KEY=
export OPENAI_DEFAULT_MODEL=
```

If you are using a Messages API endpoint (i.e. Anthropic), do this:

```
export OFF_WITH_HER_HEAD=1
```

If you are using Portkey, do this:

```
export X_PORTKEY_PROVIDER=<your_portkey_provider>
```

Now, test functionality with:

```
DEBUG_REQUESTS=1 ./lydia -p hi
```

You should see the full JSON requests dumped, and the text generation result of the request "hi".

