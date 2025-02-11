from cog import BasePredictor, Input, Path
import subprocess
import os

class Predictor(BasePredictor):

  def setup(self):
    # Set environment variables
    os.environ["OPENAI_API_KEY"] = "blah"
    os.environ["OPENAI_ENDPOINT"] = "https://openrouter.ai/api/v1"
    os.environ["FIRECRAWL_KEY"] = "stub"
    os.environ["FIRECRAWL_BASE_URL"] = "http://localhost:3002"

    # Source NVM and set up Node environment
    subprocess.run(
        'export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"',
        shell=True,
        executable='/bin/bash'
    )

    # Debug: Check environment after NVM setup
    result = subprocess.run("which node",
        shell=True,
        capture_output=True,
        text=True
    )
    print("node location:", result.stdout, result.stderr)

    # Use the full path to pnpm from npm global packages
    pnpm_path = subprocess.run(
        'export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && which pnpm',
        shell=True,
        capture_output=True,
        text=True,
        executable='/bin/bash'
    ).stdout.strip()

    # Debug: Check if directories and executables exist with explicit output capture
    result = subprocess.run("ls -la /root/.nvm/versions/node/v22.0.0/bin/",
      shell=True,
      capture_output=True,
      text=True
    )
    print("ls output:", result.stdout, result.stderr)
    result = subprocess.run("echo $PATH",
      shell=True,
      capture_output=True,
      text=True
    )
    print("PATH output:", result.stdout, result.stderr)

    # Update the commands to use the found pnpm path
    subprocess.run(
        f"cd firecrawl/apps/api && {pnpm_path} install",
        shell=True,
        check=True  # This will raise an exception if the command fails
    )
    # Start background processes
    # Redis server
    subprocess.Popen(
        "cd firecrawl && redis-server",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    # Workers
    subprocess.Popen(
        f"cd firecrawl/apps/api && {pnpm_path} run workers",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    # API server
    subprocess.Popen(
        f"cd firecrawl/apps/api && {pnpm_path} run start",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

  async def predict(self,
    openrouter_api_key: str = Input(description="OpenRouter API key"),
    query: str = Input(description="Query to research"),
    breadth: int = Input(description="Breadth of research", default=4, ge=2, le=10),
    depth: int = Input(description="Depth of research", default=2, ge=1, le=5),
  ) -> str:
    from deep_research_py import deep_research
    # Set environment variables
    os.environ["OPENAI_API_KEY"] = openrouter_api_key
    os.environ["OPENAI_ENDPOINT"] = "https://openrouter.ai/api/v1"
    os.environ["FIRECRAWL_KEY"] = "stub"
    os.environ["FIRECRAWL_BASE_URL"] = "http://localhost:3002"

    # Run deep-research command
    result = await deep_research.deep_research(query, breadth, depth, 1)

    output = "# Learnings\n\n"
    for learning in result["learnings"]:
      output += learning + "\n\n"
    output += "\n\n# Visited URLs\n\n"
    for url in result["visited_urls"]:
      output += url + "\n\n"

    return output

