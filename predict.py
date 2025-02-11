from cog import BasePredictor, Input, Path, Secret
import subprocess
import os

class Predictor(BasePredictor):

  def setup(self):
    # Set environment variables
    os.environ["OPENAI_API_KEY"] = "blah"
    os.environ["OPENAI_ENDPOINT"] = "https://openrouter.ai/api/v1"
    os.environ["FIRECRAWL_KEY"] = "stub"
    os.environ["FIRECRAWL_BASE_URL"] = "http://localhost:3002"

    # Initialize NVM and install Node.js if needed
    setup_commands = [
        'export NVM_DIR="$HOME/.nvm"',
        '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"',  # This loads nvm
        'nvm install 22',
        'nvm use 22',
        'npm install -g pnpm'
    ]

    setup_result = subprocess.run(
        ' && '.join(setup_commands),
        shell=True,
        capture_output=True,
        text=True,
        executable='/bin/bash'
    )

    print("Setup output:", setup_result.stdout)
    print("Setup errors:", setup_result.stderr)

    # Now get the pnpm path after setup
    pnpm_result = subprocess.run(
        'export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh" && which pnpm',
        shell=True,
        capture_output=True,
        text=True,
        executable='/bin/bash'
    )

    if pnpm_result.returncode != 0:
        print("Error finding pnpm:", pnpm_result.stderr)
        raise RuntimeError("Failed to find pnpm")

    pnpm_path = pnpm_result.stdout.strip()
    self.pnpm_path = pnpm_path
    print(f"Found pnpm at: {pnpm_path}")

    # Run the install command with the full environment setup
    install_cmd = f'export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh" && cd firecrawl/apps/api && {pnpm_path} install'
    install_result = subprocess.run(
        install_cmd,
        shell=True,
        capture_output=True,
        text=True,
        executable='/bin/bash'
    )

    if install_result.returncode != 0:
        print("Error during pnpm install:", install_result.stderr)
        raise RuntimeError("Failed to run pnpm install")

    # Start background processes with the proper environment
    env_prefix = 'export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh" && '
    self.env_prefix = env_prefix

    # Redis server
    subprocess.Popen(
        f"{env_prefix}cd firecrawl && redis-server",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

  async def predict(self,
    openrouter_api_key: Secret = Input(description="OpenRouter API key"),
    searchapi_api_key: Secret = Input(description="SearchAPI API key"),
    query: str = Input(description="Query to research"),
    breadth: int = Input(description="Breadth of research", default=4, ge=2, le=10),
    depth: int = Input(description="Depth of research", default=2, ge=1, le=5),
  ) -> str:
    # Set environment variables
    os.environ["OPENAI_API_KEY"] = openrouter_api_key.get_secret_value()
    os.environ["OPENAI_API_ENDPOINT"] = "https://openrouter.ai/api/v1"
    os.environ["FIRECRAWL_KEY"] = "stub"
    os.environ["FIRECRAWL_BASE_URL"] = "http://localhost:3002"
    os.environ["SEARCHAPI_API_KEY"] = searchapi_api_key.get_secret_value()
    os.environ["SEARCHAPI_ENGINE"] = "google"
    from deep_research_py import deep_research
    # Workers
    subprocess.Popen(
        f"{self.env_prefix}cd firecrawl/apps/api && {self.pnpm_path} run workers",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # API server
    subprocess.Popen(
        f"{self.env_prefix}cd firecrawl/apps/api && {self.pnpm_path} run start",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    import time
    time.sleep(10)

    # Run deep-research command
    result = await deep_research.deep_research(query, breadth, depth, 1)
    report = await deep_research.write_final_report(query, result["learnings"], result["visited_urls"])

    output = "# Learnings\n\n"
    for learning in result["learnings"]:
      output += learning + "\n\n"
    output += "\n\n# Visited URLs\n\n"
    for url in result["visited_urls"]:
      output += url + "\n\n"

    return report + "\n\n--------------------------\n\n" + output

