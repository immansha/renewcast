"""
train_rl_policy.py
Pre-trains the RL dispatch policy. Run once before the demo.
Saves the policy to models/dispatch_policy.zip

Run: python scripts/train_rl_policy.py
"""

import os
import numpy as np

try:
    import gymnasium as gym
    from gymnasium import spaces
    from stable_baselines3 import PPO
    from stable_baselines3.common.env_util import make_vec_env
    HAS_SB3 = True
except ImportError:
    HAS_SB3 = False


class GridDispatchEnv(gym.Env if HAS_SB3 else object):
    """
    Observation: [p10, p50, p90, demand, hour_of_day]
    Action:      0=no backup  1=hydro (fast)  2=gas (slow)
    Reward:      penalises unmet demand and over-dispatch
    """
    metadata = {"render_modes": []}

    def __init__(self):
        super().__init__()
        self.observation_space = spaces.Box(
            low=np.array([0, 0, 0, 0, 0], dtype=np.float32),
            high=np.array([200, 200, 200, 200, 24], dtype=np.float32))
        self.action_space = spaces.Discrete(3)
        self.step_count   = 0

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.step_count = 0
        return self._obs(), {}

    def _obs(self):
        hour      = np.random.uniform(0, 24)
        solar_base = max(0, 80 * np.sin(np.pi * (hour - 6) / 12))
        p50       = solar_base * np.random.uniform(0.8, 1.2)
        spread    = p50 * np.random.uniform(0.1, 0.4)
        demand    = np.random.uniform(60, 90)
        return np.array([max(0, p50 - spread), p50, min(100, p50 + spread),
                         demand, hour], dtype=np.float32)

    def step(self, action):
        obs        = self._obs()
        p50, demand = obs[1], obs[3]
        backup_mw  = [0, 50, 80][action]
        total      = p50 + backup_mw
        unmet      = max(0, demand - total)
        over       = max(0, total - demand - 10)
        cost       = 2 if action == 1 else 0
        reward     = -(unmet * 2 + over * 0.5 + cost)
        self.step_count += 1
        return obs, reward, self.step_count >= 200, False, {}


def train():
    if not HAS_SB3:
        print("stable-baselines3 not installed.")
        print("Run: pip install stable-baselines3 gymnasium")
        return

    os.makedirs("./models", exist_ok=True)
    print("Training RL dispatch policy (50k steps)...")

    env   = make_vec_env(GridDispatchEnv, n_envs=4)
    model = PPO("MlpPolicy", env, verbose=1,
                learning_rate=3e-4, n_steps=512,
                batch_size=64, n_epochs=10, gamma=0.99)
    model.learn(total_timesteps=50_000)
    model.save("./models/dispatch_policy")
    print("Policy saved to ./models/dispatch_policy.zip")


if __name__ == "__main__":
    train()
