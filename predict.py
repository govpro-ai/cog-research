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

    # First run pnpm install and wait for it to complete
    subprocess.run(
      "cd firecrawl/apps/api && /root/.nvm/versions/node/v22.0.0/bin/pnpm install",
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
      "cd firecrawl/apps/api && /root/.nvm/versions/node/v22.0.0/bin/pnpm run workers",
      shell=True,
      stdout=subprocess.DEVNULL,
      stderr=subprocess.DEVNULL
    )
    # API server
    subprocess.Popen(
      "cd firecrawl/apps/api && /root/.nvm/versions/node/v22.0.0/bin/pnpm run start",
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

