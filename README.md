

<p align='center'><img src="assets/ghostbit.png" width='180' alt="img"></p>

<p align='center'>GH0STB1T:<br>A M<small>ULTI-</small>F<small>ORMAT</small> S<small>TEGANOGRAPHY</small> T<small>OOLKIT</small></p>

<p align="center">
  <a href="https://www.apache.org/licenses/LICENSE-2.0">
    <img src="https://img.shields.io/badge/License-Apache%202.0-red.svg" alt="License">
  </a>
  <a href="https://github.com/kariemoorman/ghostbit/releases">
    <img src="https://img.shields.io/github/v/release/kariemoorman/ghostbit?cacheSeconds=300" alt="Release">
  </a>
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/python-3.13+-purple.svg" alt="Language">
  </a>
  <a href="https://img.shields.io/github/languages/code-size/kariemoorman/ghostbit">
    <img src="https://img.shields.io/github/languages/code-size/kariemoorman/ghostbit" alt="Code Size">
  </a>
</p>
<p align='center'>
  <a href="https://github.com/kariemoorman/ghostbit/actions/workflows/security.yml/badge.svg">
    <img src="https://github.com/kariemoorman/ghostbit/actions/workflows/security.yml/badge.svg" alt="Security">
  </a>
  <a href="https://github.com/kariemoorman/ghostbit/actions/workflows/test.yml/badge.svg">
    <img src="https://github.com/kariemoorman/ghostbit/actions/workflows/test.yml/badge.svg" alt="Tests">
  </a>
  <a href="https://github.com/kariemoorman/ghostbit">
    <img src="https://img.shields.io/codecov/c/github/kariemoorman/ghostbit?logo=codecov&logoColor=white" alt="Coverage">
  </a>
</p>


---

## Why?

<details>
<summary><b>Architectural Modernization</b></summary>

<br>

This implementation represents a complete architectural migration from platform-dependent Java and .NET codebases to a unified Python solution, delivering:

- **Platform Independence:** Eliminates platform-specific runtime dependencies, ensuring portability across heterogeneous computing environments (Windows, macOS, and Linux). 

- **Memory Efficiency:** Eliminates JVM heap overhead, reducing baseline memory consumption and enabling efficient operation on resource-constrained systems while maintaining full functionality.

- **Auditability:** Eliminates reliance on platform-specific cryptographic APIs or closed-source runtime components in favor of open-source Python cryptography, enabling independent security audits and transparent verification of the implementation.

- **Type Safety:** This implementation targets Python 3.13+ to leverage modern type annotations and static analysis capabilities, ensuring type safety across the entire codebase.

These improvements reduce deployment complexity and computational overhead, facilitating reliable and efficient operation in resource-constrained environments for both human operators and automated LLM-driven workflows.

(see also [EFF Coders' Rights Project Reverse Engineering FAQ](https://www.eff.org/issues/coders/reverse-engineering-faq#faq5))


</details>

<details>
<summary><b>Security Upgrade</b></summary>

<br>

Longstanding steganography tools (e.g., [OpenStego](https://www.openstego.com/), [DeepSound](https://github.com/Jpinsoft/DeepSound), [SilentEye](https://github.com/achorein/silenteye/)) use outdated cryptographic primitives that leave hidden data vulnerable to attack. These tools rely on weak key derivative functions (KDFs) such as direct hashing of passwords using MD5, SHA-1, or SHA-256, which provide no brute-force resistance. They also rely on legacy encryption modes such as AES-CBC without authentication. These modes provide confidentiality only, leaving payloads vulnerable to undetected modification, bit-flipping attacks, and—under common error-handling patterns—padding decryption. 

This implementation pairs existing steganography protocols with modern, audited cryptographic standards to ensure secure information hiding:

| Component | Algorithm | Parameters | Security Properties |
|-----------|-----------|------------|---------------------|
| **Key Derivation** | Argon2id | 64MB memory, 3 iterations, parallelism=4 | - Memory-hard function<br> - Hybrid protection against side-channel attacks |
| **Encryption** | AES-256-GCM | 96-bit random nonce, 128-bit auth tag | - Authenticated Encryption with Associated Data (AEAD)<br>- Confidentiality + Integrity + Authenticity in single operation |
| **Salt** | Random | 128-bit, unique per file | - Prevention against rainbow table attacks<br> - Unique keys even with identical passwords |

<details>
<summary><b>What Does This Mean?</b></summary>

<br>

**NIST/FIPS Compliant Cryptography**
- Transition to algorithms approved by national security standards (Argon2id, AES-256-GCM); the same cryptographic primitives used in TLS 1.3, Signal, Bitwarden, and enterprise security systems.

**Uncrackable Passwords**
- Legacy SHA-256 allows attackers to test billions of passwords per second on modern GPUs. Argon2id slows attackers to only thousands of tests per second, making brute-force attacks impractical (memory-hard by design). Even weak passwords (8 characters) gain years of protection against brute-force attacks.

**Tamper Detection & Integrity Verification**
- Legacy AES-CBC allows for undetected tampering, bit-flipping attacks, and payload manipulation. AES-GCM cryptographically authenticates every byte of hidden data. Any modification (e.g., a single bit flip) causes immediate decryption failure. It is now mathematically impossible to alter data without detection.

**Elimination of Padding Oracle Vulnerabilities**
- Legacy AES-CBC with PKCS#7 padding is vulnerable to adaptive chosen-ciphertext attacks. Attackers can decrypt data without the password by observing error messages. AES-GCM uses authenticated encryption: no padding, no oracle, constant-time failure.


</details>

<br>

</details>


---

## Features

<b>Multimedia Steganography:</b> Multi-format support across audio, images, and video  
 • Audio: WAV / MP3 / FLAC / M4A / AIFF  
 • Image: BMP / PNG / JPEG / WEBP / TIFF / SVG / GIF

<b>Strong Encryption:</b> AES-GCM with Argon2id key derivation for embedded files (see [Security Upgrade](#why))

<b>CLI:</b> Easy-to-use command line interface (see [CLI](#-cli))

<b>API:</b> Project integration via API (see [API](#-python-api))

<b>Docker:</b> Containerized deployment support (see [Docker](#-docker))

<b>LLM Integration:</b> Built-in skills system for LLM-driven workflows (see [LLM Integration](#llm-integration))

<b>Cross-Platform Compatibility:</b> MacOS, Linux, Windows



## Installation

<b>Requirements</b>

- Python 3.13+
- FFmpeg (for audio format conversion)

<br>

<b>GitHub Release</b>

Download the latest `.whl` file from [Releases](https://github.com/kariemoorman/ghostbit/releases):

```bash
pip install git+https://github.com/kariemoorman/ghostbit.git@latest
```

<b>Development Build</b>

Install from source for development or to access the latest features:

```bash
git clone https://github.com/kariemoorman/ghostbit.git
cd ghostbit
pip install -e ".[dev]"
```

---

## Usage

### CLI

GH0STB1T CLI provides quick encoding/decoding/analysis operations directly from the terminal.


<details>
<summary><b>Encode (Hide files)</b></summary>

<br> 

```bash
# Audio
ghostbit audio encode -i <audio_filepath> -s <secret_filepath> <secret_filepath> -q {low,normal,high} -o <output_filename>.<desired_format> -p

# Image
ghostbit image encode -i <image_filepath> -s <secret_filepath> <secret_filepath> -p

```

</details>

<details>
<summary><b>Calculate Carrier Capacity</b></summary>

<br> 

```bash
# Audio
ghostbit audio capacity -i <audio_filepath> -q {low,normal,high}

# Image
ghostbit image capacity -i <image_filepath> 

```

</details>

<details>
<summary><b>Decode (Extract Files)</b></summary>

<br>

```bash
# Audio
ghostbit audio decode -i <audio_filepath> -p

# Image
ghostbit image decode -i <image_filepath> -p

```

</details>

<details>
<summary><b>Analyze File</b></summary>

<br>


```bash
# Audio
ghostbit audio analyze -i <audio_filepath>

# Image
ghostbit image analyze -i <image_filepath>

```

</details>

<details>
<summary><b>Create Test Files</b></summary>

<br>


```bash
# Audio Creation for Testing
ghostbit audio test -o test_audio

# Image Creation for Testing
ghostbit image test -o test_images

```

</details>

<br>

### Python API

GH0STB1T provides a Python API for seamless integration into existing applications and workflows.

<details>
<summary><b>Encode (Hide files)</b></summary>

<br>

```python
from ghostbit.audiostego import AudioMultiFormatCoder, EncodeMode

# Initialize coder
coder = AudioMultiFormatCoder()

# Encode files
coder.encode_files_multi_format(
    carrier_file="music.wav",
    secret_files=["document.pdf", "image.jpg"],
    output_file="output.wav",
    quality_mode=EncodeMode.NORMAL_QUALITY,
    password="optional_password"
)
```

```python
# Encoding with Progress Callbacks
from ghostbit.audiostego import AudioMultiFormatCoder

coder = AudioMultiFormatCoder()

# Encoding progress
def on_encode_progress():
    print(".", end="", flush=True)

coder.on_encoded_element = on_encode_progress

coder.encode_files_multi_format(
    carrier_file="carrier.wav",
    secret_files=["secret.pdf"],
    output_file="output.wav"
)
```

</details>

<details>
<summary><b>Calculate Carrier Capacity</b></summary>

<br>

```python
from ghostbit.audiostego import AudioMultiFormatCoder, BaseFileInfoItem, EncodeMode

coder = AudioMultiFormatCoder()
wav_file = coder._convert_to_wav("carrier_file.flac")

def get_capacity(wav_file, encode_mode):

    base_file = BaseFileInfoItem(
        full_path=wav_file,
        encode_mode=encode_mode,
        wav_head_length=44,
    )
    return base_file.max_inner_files_size

capacity_bytes = get_capacity(wav_file, EncodeMode.NORMAL_QUALITY)

print(f"Maximum capacity: {capacity_bytes / (1024*1024):.2f} MB")
```

```python
from ghostbit.audiostego import AudioMultiFormatCoder, EncodeMode
import os

coder = AudioMultiFormatCoder()

# Check capacity with different quality modes
carrier = "long_audio.wav"
secret_file = "large_video.mp4"
secret_size = os.path.getsize(secret_file) / (1024 * 1024)

print(f"Secret file size: {secret_size:.2f} MB")

for mode in [EncodeMode.LOW_QUALITY, EncodeMode.NORMAL_QUALITY, EncodeMode.HIGH_QUALITY]:
    capacity = get_capacity(carrier, mode) / (1024 * 1024)
    fits = "✅ FITS" if capacity >= secret_size else "❌ TOO LARGE"
    print(f"{mode.name}: {capacity:.2f} MB capacity - {fits}")
```

</details>

<details>
<summary><b>Decode (Extract Files)</b></summary>

<br>

```python
from ghostbit.audiostego import AudioMultiFormatCoder

# Initialize coder
coder = AudioMultiFormatCoder()

# Decode files
coder.decode_files_multi_format(
    encoded_file="output.wav",
    output_dir="extracted/",
    password="optional_password"
)
```

```python
# Decode with Progress Callbacks
from ghostbit.audiostego import AudioMultiFormatCoder

coder = AudioMultiFormatCoder()

# Decoding progress
def on_decode_progress():
    print(".", end="", flush=True)

coder.on_decoded_element = on_decode_progress

coder.decode_files_multi_format(
    encoded_file="output.wav",
    output_dir="extracted/"
)
```

</details>

<details>
<summary><b>Password Protection</b></summary>

<br>

```python
from ghostbit.audiostego import AudioMultiFormatCoder, KeyRequiredEventArgs

coder = AudioMultiFormatCoder()

# Handle password requests during decoding
def request_password(args: KeyRequiredEventArgs):
    password = input(f"Enter password (version {args.h22_version}): ")
    if password:
        args.key = password
    else:
        args.cancel = True  # Cancel operation

coder.on_key_required = request_password

coder.decode_files_multi_format(
    encoded_file="encrypted_output.wav",
    output_dir="extracted/"
)
```

```python
# Password-Protected Multiple Files
from ghostbit.audiostego import AudioMultiFormatCoder, EncodeMode

coder = AudioMultiFormatCoder()

# Encode with password
coder.encode_files_multi_format(
    carrier_file="music.mp3",
    secret_files=[
        "report.pdf",
        "spreadsheet.xlsx",
        "presentation.pptx"
    ],
    output_file="encoded_music.mp3",
    quality_mode=EncodeMode.HIGH_QUALITY,
    password="SuperSecure123!"
)

print("✅ Multiple files encrypted and hidden!")

# Decode
coder.decode_files_multi_format(
    encoded_file="encoded_music.mp3",
    output_dir="extracted_files/",
    password="SuperSecure123!"
)

print("✅ Files extracted successfully!")
```

</details>

<br>

### Docker

GH0STB1T can be deployed using Docker for isolated, reproducible environments.


<details>
<summary><b>Initial Setup</b></summary>

<br>

1. **Clone the repository:**

```bash
git clone https://github.com/kariemoorman/ghostbit.git
cd ghostbit
```

2. **Create local `input` and `output` directories:**

These local directories are mapped to Docker container directories, ensuring secure file access.
```bash
mkdir input output
```

3. **Place your files in the `input/` directory:**

```bash
cp /path/to/carrier.wav input/
cp /path/to/secret.pdf input/
```

</details>


<details>
<summary><b>Build & Run</b></summary>

<br>

```bash
# Build and start the container
docker-compose up -d ghostbit

# Encode files
docker-compose exec ghostbit ghostbit audio encode -i input/carrier.wav -f /input/secret.pdf -o encoded.wav -p

# Decode files
docker-compose exec ghostbit ghostbit audio decode -i output/encoded.wav  -p 

# Check capacity
docker-compose exec ghostbit ghostbit audio capacity input/carrier.wav -q high

# Analyze file
docker-compose exec ghostbit ghostbit audio analyze -i output/encoded.wav -p
```

</details>

<details>
<summary><b>Cleanup</b></summary>

<br>

```bash
# Stop the container
docker-compose stop

# Remove the container
docker-compose down

# Remove container and images
docker-compose down --rmi all
```

</details>


---

## LLM Integration

### MCP Server 

GH0STB1T includes an MCP Server for standardized and secure integration with LLM-based systems, supporting 10 tools: 

[GH0STB1T MCP Server](https://github.com/kariemoorman/ghostbit/blob/main/src/ghostbit/mcp_server)

|Audio|Image|
|--|--|
|- audio_encode | - image_encode |
|- audio_decode | - image_decode |
|- audio_capacity | - image_capacity |
|- audio_analyze | - image_analyze |
|- generate_audio_carrier | - generate_image_carrier |



Security hardening measures include:
- Increased password security, ensuring passwords never flow through the AI model's context
- Type-annotated tool parameters that auto-generate JSON schemas via FastMCP
- Input sanitization, including null bytes & control characters rejection, path normalization, shell metacharacter rejection, pattern validation
- Filesystem sandbox, limiting I/O to only designated and resolvable paths
- Symlink rejection, blocking symbolic links on all input files
- Prompt injection defense including filename sanitization
- Error sanitization, ensuring errors are translated into safe category-level messages
- Audit logging and password scrubbing
- Stateless tool design (fresh coder instance per call)
- Resource exhaustion prevention, including file size limits and stateless tool calls

Instructions for setting up the MCP Server are provided below:
<details>
<summary><b>Password Management</b></summary>

<br> 
Unlike the CLI, MCP Servers require an additional layer of security to prevent LLMs from accessing the passwords used to encrypt/decrypt secret files encoded in digital media. 

For this reason, users must first prepare a password file, either encrypted using SOPS or plaintext (with read-only permissions).

### SOPS
```
brew install sops age 
```
```
# Create the directory
mkdir -p ~/.config/sops/age

# Generate the key
age-keygen -o ~/.config/sops/age/keys.txt

chmod 600 ~/.config/sops/age/keys.txt
chmod 700 ~/.config/sops/age
chmod 700 ~/.config/sops

# Now get the public key
AGE_PUB=$(grep "public key" ~/.config/sops/age/keys.txt | awk '{print $NF}')

# Create config in home directory
cat > ~/.sops.yaml << EOF
creation_rules:
  - age: "$AGE_PUB"
EOF
```

```
# Create password file
echo -n "demo123" > ~/.ghostbit-pw.txt
#Encrypt the file using SOPS + age
sops -e ~/.ghostbit-pw.txt > ~/.ghostbit-pw.enc
```
```
# Should print your password
sops -d ~/.ghostbit-pw.enc
```

```
password_file='~/.ghostbit-pw.enc'
```


### Plaintext 
```
echo -n "demo123" > ~/.ghostbit-password
chmod 600 ~/.ghostbit-password
```
```
password_file="~/.ghostbit-password"
```

</details>


<details>
<summary><b>Onboarding MCP Server</b></summary> 

<br> 

Ensure the GH0STB1T MCP package is installed in a virtual environment: 

```
cd /path/to/ghostbit
python -m venv .ghostbit-venv
source .ghostbit-venv/bin/activate
pip install -e '.[mcp]'
```
  

#### LM Studio/Cursor

Option 1: Use General Command
mcp.json
```
{
  "mcpServers": {
    "ghostbit": {
      "command": "/path/to/ghostbit/.ghostbit-venv/bin/ghostbit-mcp"
    }
  }
}
```

Option 2: Use General Command with GHOSTBIT_ALLOWED_DIRS
mcp.json
```
{
  "mcpServers": {
    "ghostbit": {
      "command": "/path/to/ghostbit/.ghostbit-venv/bin/ghostbit-mcp",
      "env": {
        "GHOSTBIT_ALLOWED_DIRS": "/path/to/ghostbit/output:/path/to/ghostbit/tests/testcases"
      }
    }
  }
}

```

</details>


<details>
<summary><b>Example Prompts</b></summary>

#### Audio

1. Generate a carrier audio file

* "Use generate_audio_carrier to create a WAV file at /path/to/outputdir/carrier.wav with duration 5 seconds, frequency 440 Hz, sample rate 44100, and 1 channel"

2. Check capacity

* "Use audio_capacity to check how much data /path/to/output/carrier.wav can hide with quality 'normal'"

3. Encode a secret file

* "Use audio_encode to hide /path/to/directory/test_document.txt inside /path/to/outputdir/carrier.wav, save output to /path/to/output/encoded_audio.wav, quality 'normal', password_file='~/.ghostbit-password'"

4. Analyze for hidden data

* "Use audio_analyze on /path/to/output/encoded_audio.wav with password_file='~/.ghostbit-password'"

5. Decode and extract

* "Use audio_decode on /path/to/output/encoded_audio.wav, output to /path/to/output/decoded, password_file='~/.ghostbit-password'"

6. Full end-to-end (single prompt)

* "Generate a 10-second 440Hz WAV carrier at /path/to/output/stego_carrier.wav, then check its capacity at all three quality modes (low, normal, high), then hide /path/to/test_document.txt in it with quality 'low' and password_file='~/.ghostbit-password' saving to /path/to/output/stego_audio.wav, then analyze the result"

#### Image

1. Generate a carrier image

* "Use generate_image_carrier to create a PNG image at /path/to/output/carrier.png with width 800, height 600, and a gradient pattern"

2. Check capacity

* "Use image_capacity to check how much data /path/to/output/carrier.png can hide"

3. Encode a secret file

* "Use image_encode to hide /path/to/testcases/test_document.txt inside /path/to/output/carrier.png, save output to /path/to/output/encoded_image, password_file='~/.ghostbit-pw.enc'"

4. Analyze for hidden data
   
* "Use image_analyze on /path/to/output/encoded_image/carrier.png"

5. Decode and extract
   
* "Use image_decode on /path/to/output/carrier.png, output to /path/to/output/decoded_image, password_file='~/.ghostbit-pw.enc'"

6. Full end-to-end (single prompt)

* "Generate a 1000x1000 waves pattern PNG at /path/to/output/stego_cover.png, then check its capacity, then hide /path/to/test_document.txt in it with password_file='~/.ghostbit-pw.enc', saving to /path/to/output/encoded, then analyze the result"

</details>


### Skills

GH0STB1T includes a Skills system designed for seamless integration with LLMs and AI assistants.

#### Available Skills

GH0STB1T provides specialized skill documents:

1. [**Audio Steganography**](https://github.com/kariemoorman/ghostbit/blob/main/src/ghostbit/audiostego/skills/steganography/SKILL.md) - Complete usage guide with examples
2. [**Audio Capacity**](https://github.com/kariemoorman/ghostbit/blob/main/src/ghostbit/audiostego/skills/capacity/SKILL.md) - Capacity planning and optimization strategies
3. [**Audio Troubleshooting**](https://github.com/kariemoorman/ghostbit/blob/main/src/ghostbit/audiostego/skills/troubleshooting/SKILL.md) - Common issues and solutions
4. [**Image Steganography**](https://github.com/kariemoorman/ghostbit/blob/main/src/ghostbit/imagestego/skills/steganography/SKILL.md) - Complete usage guide with examples
5. [**Image Capacity**](https://github.com/kariemoorman/ghostbit/blob/main/src/ghostbit/imagestego/skills/capacity/SKILL.md) - Capacity planning and optimization strategies
6. [**Image Troubleshooting**](https://github.com/kariemoorman/ghostbit/blob/main/src/ghostbit/imagestego/skills/troubleshooting/SKILL.md) - Common issues and solutions

#### Quick Start for LLMs

<details>
<summary><b>Retrieve Documentation</b></summary>

<br>

```python
from ghostbit.audiostego import get_audio_llm_context

# Get complete documentation formatted for LLMs
context = get_audio_llm_context()

# Use in your LLM prompt
prompt = f"""
You are an expert in audio steganography using AudioStego.

{context}

User: How do I hide a 5MB PDF in a 10-minute WAV file with maximum security?

Please provide a complete Python example with security best practices.
"""

# Send prompt to your LLM
# response = your_llm_api(prompt)
```

</details>

<details>
<summary><b>Load Specific Skills</b></summary>

<br>

```python
from ghostbit.audiostego import load_audio_skill

# Load a specific skill
stego_skill = load_audio_skill("steganography")

# Get skill content
print(stego_skill.content)

# Get examples from skill
examples = stego_skill.get_examples()
for example in examples:
    print(f"Language: {example['language']}")
    print(f"Description: {example['description']}")
    print(f"Code:\n{example['code']}\n")

# Get specific section
best_practices = stego_skill.get_section("Best Practices")
print(best_practices)
```

</details>

<details>
<summary><b>Create a Prompt Template</b></summary>

<br>

```python
from ghostbit.audiostego import get_audio_llm_context

# Prepare context
skills_context = get_audio_llm_context()

# Create detailed prompt
prompt = f"""
You are an expert Python developer specializing in audio steganography.

CONTEXT:
{skills_context}

TASK:
The user wants to create a secure file hiding system for sensitive documents.

Requirements:
- Hide multiple PDF files in a single audio carrier
- Use strong encryption with user-provided passwords
- Show progress during encoding/decoding
- Handle errors gracefully
- Verify file integrity after extraction

USER QUESTION: {user_question}

Please provide:
1. Complete working code
2. Security considerations
3. Error handling strategy
4. Usage example

Format your response as:
- Code blocks with explanations
- Security notes
- Example usage
"""

# Send to LLM API
# response = llm_api.generate(prompt)
```

</details>


<details>
<summary><b>Integrate with Anthropic Claude API</b></summary>

<br>

```python
import anthropic
from ghostbit.audiostego import get_audio_llm_context

client = anthropic.Anthropic(api_key="your-api-key")
context = get_audio_llm_context()

message = client.messages.create(
    model="claude-3-opus-20240229",
    max_tokens=2048,
    system=f"You are an AudioStego expert.

{context}",
    messages=[
        {"role": "user", "content": "Show me how to use AudioStego with error handling"}
    ]
)

print(message.content[0].text)
```

</details>


<details>
<summary><b>Integrate with OpenAI API</b></summary>


```python
from openai import OpenAI
from ghostbit.audiostego import get_audio_llm_context

client = OpenAI(api_key="your-api-key")
context = get_audio_llm_context()

response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": f"You are an AudioStego expert.

{context}"},
        {"role": "user", "content": "How do I encode files with maximum security?"}
    ]
)

print(response.choices[0].message.content)
```

</details>



---

## Troubleshooting

- **GitHub Issues:** [Report bugs or request features](https://github.com/kariemoorman/ghostbit/issues)
- **Discussions:** [Ask questions and share ideas](https://github.com/kariemoorman/ghostbit/discussions)
- **Documentation:** [Full API reference](https://github.com/kariemoorman/ghostbit/wiki)

---

## Contributions

Contributions are welcome! 

Here's how to get started: [CONTRIBUTING.md](https://github.com/kariemoorman/ghostbit/blob/main/CONTRIBUTING.md)


--- 

## Citation

GH0STB1T is a free and open source education and research tool. If you use GH0STB1T in your research or project, please cite it as:

```bibtex
@software{audiostego2026,
  author = {Karie Moorman},
  title = {GH0STB1T: A Multi-format Steganography Toolkit for Python},
  year = {2026},
  url = {https://github.com/kariemoorman/ghostbit},
  version = {0.0.3}
}
```


**APA Format:**
```
Moorman, Karie. (2026). GH0STB1T: A Multi-format Steganography Toolkit for Python (Version 0.0.1) [Computer software]. https://github.com/kariemoorman/ghostbit
```


---

## License

This project is licensed under the [Apache License 2.0 LICENSE](LICENSE).
