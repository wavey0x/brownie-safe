# Brownie Safe: Gnosis Safe tx builder

[Read Documentation](https://safe.ape.tax/)

Brownie Safe allows you to iteratively build complex multi-step Gnosis Safe transactions and safely preview their side effects from the convenience of a locally forked mainnet environment.

*Previously known as Ape Safe*

## Installation

```
uv pip install brownie-safe --pre
```

## Quickstart

```bash
brownie console --network mainnet-fork
```

```python
from brownie_safe import BrownieSafe
safe = BrownieSafe('ychad.eth')

dai = safe.contract('0x6B175474E89094C44Da98b954EedeAC495271d0F')
vault = safe.contract('0x19D3364A399d251E894aC732651be8B0E4e85001')

amount = dai.balanceOf(safe.account)
dai.approve(vault, amount)
vault.deposit(amount)

safe_tx = safe.multisend_from_receipts()
safe.preview(safe_tx)
safe.post_transaction(safe_tx)
```

See [Documentation](https://safe.ape.tax/) for more examples and full reference.

## Safe API Migration

Brownie Safe now supports Safe's authenticated Transaction Service API with minimal changes to your existing code. This migration ensures compatibility with Safe's new API requirements while maintaining backwards compatibility.

### Environment Variables

Set these environment variables to configure the Safe Transaction Service integration:

#### Required
- `SAFE_TRANSACTION_SERVICE_API_KEY` - Your Safe API key ([get one here](https://api.safe.global))

#### Optional Configuration
- `SAFE_TX_SERVICE_BASE` - Custom base URL (default: `https://api.safe.global/tx-service`)
- `SAFE_TX_SERVICE_CHAIN` - Override chain code for custom networks
- `SAFE_TX_TIMEOUT_SEC` - Request timeout in seconds (default: `20`)  
- `SAFE_TX_RETRIES` - Number of retries for failed requests (default: `3`)
- `SAFE_TX_ALLOW_NO_KEY` - Set to `true` to suppress API key requirement in development

### Supported Networks

The following networks are automatically mapped to their Safe API chain codes:

| Network | Chain ID | Chain Code |
|---------|----------|------------|
| Ethereum | 1 | `eth` |
| Optimism | 10 | `oeth` |
| Base | 8453 | `base` |
| Arbitrum One | 42161 | `arb1` |
| Gnosis Chain | 100 | `gno` |
| Polygon | 137 | `matic` |
| BNB Chain | 56 | `bnb` |

Unknown networks default to `eth` with a warning.

### Basic Setup

```bash
# Set your API key
export SAFE_TRANSACTION_SERVICE_API_KEY="your-api-key-here"

# Optional: Enable development mode (no API key required)
export SAFE_TX_ALLOW_NO_KEY="true"
```

### Usage Example

```python
from brownie_safe import BrownieSafe

# Works the same as before - authentication handled automatically
safe = BrownieSafe('your-safe.eth')
safe_tx = safe.multisend_from_receipts()
safe.post_transaction(safe_tx)  # Now uses authenticated API
```

### Validation

Test your configuration with the included validation script:

```bash
python validate_safe_api.py
```

This script will verify:
- Environment configuration
- Chain code resolution  
- API connectivity and authentication
- Request headers and retry logic

### Migration Notes

- **Backwards Compatible**: Existing code continues to work without changes
- **Automatic Fallback**: Falls back to old API methods if new API fails
- **Rate Limiting**: Built-in retry logic handles rate limits (HTTP 429)
- **Error Handling**: Clear error messages for common issues (401, missing API key)

### Troubleshooting

**401 Unauthorized Error**: Check that `SAFE_TRANSACTION_SERVICE_API_KEY` is set correctly

**Rate Limited (429)**: The client automatically retries with exponential backoff

**Unknown Chain Warning**: Set `SAFE_TX_SERVICE_CHAIN` to override chain detection

**Development Mode**: Set `SAFE_TX_ALLOW_NO_KEY=true` to bypass API key requirement for local testing
