from ray.rllib.algorithms.ppo import PPOConfig

# Create a config instance for the PPO algorithm.
config = (
    PPOConfig()
    .environment("Pendulum-v1")
)

config.env_runners(num_env_runners=2)

config.training(
    lr=0.0002,
    train_batch_size_per_learner=2000,
    num_epochs=10,
)

# Build the Algorithm (PPO).
ppo = config.build_algo()

# pprint可以将返回的多嵌套字段的字典结果输出，ppo.train()返回训练中各种信息
"""
有一些常用的结果和字段：
episode_reward_mean	平均回报	最重要指标。最近 100 个回合的平均得分。越高越好。
episode_reward_max	最大回报	最近的历史记录中出现的最高分。
episode_reward_min	最小回报	最近的历史记录中出现的最低分（用于检查最差情况）。
episode_len_mean	平均回合长度	存活了多久。对于某些任务（如倒立摆），越长通常越好；对于竞速任务，越短越好。

training_iteration迭代次数ppo.train() 被调用的次数（第几轮）。
num_env_steps_sampled总采样步数Agent 与环境交互的总步数（包含所有 Worker）。
time_total_s总耗时 (秒)训练开始到现在的物理时间。
timesteps_total总时间步同 num_env_steps_sampled，通常用于横坐标绘图。

ppo内部的：
entropy	熵 (随机性)	
非常重要。表示策略的随机程度。


• 太高: 还在瞎猜，没收敛。


• 太低 (接近0): 过早收敛，可能陷入局部最优，不再探索。

policy_loss	策略损失	优化 Actor 网络的 Loss。通常应该震荡下降。
vf_loss	价值损失	优化 Critic (Value Function) 的 Loss。表示它对分数的预测准不准。
kl	KL 散度	新旧策略的差异。PPO 试图限制这个值，如果它突然变得很大，说明训练不稳定。
"""
from tools import print_train_and_eval_status


for _ in range(1):
    # pprint(ppo.train())
    print_train_and_eval_status(ppo.train())

# 保存模型
checkpoint_path = ppo.save_to_path()

# 带测试的训练
config.evaluation(
    # Run one evaluation round every iteration.
    evaluation_interval=1,

    # Create 2 eval EnvRunners in the extra EnvRunnerGroup.
    evaluation_num_env_runners=2,

    # Run evaluation for exactly 10 episodes. Note that because you have
    # 2 EnvRunners, each one runs through 5 episodes.
    evaluation_duration_unit="episodes",
    evaluation_duration=10,
)

# Rebuild the PPO, but with the extra evaluation EnvRunnerGroup
ppo_with_evaluation = config.build_algo()

for _ in range(1):
    # pprint(ppo_with_evaluation.train())
    print_train_and_eval_status(ppo_with_evaluation.train())

# 如何使用 Ray Tune 配合 RLlib 进行 超参数调优
from ray import tune
from ray.rllib.algorithms.ppo import PPOConfig

config = (
    PPOConfig()
    .environment("Pendulum-v1")
    # Specify a simple tune hyperparameter sweep.
    .training(
        lr=tune.grid_search([0.001, 0.0005, 0.0001]), # 参数搜索
    )
)

# Create a Tuner instance to manage the trials.
tuner = tune.Tuner(
    config.algo_class,
    param_space=config,
    # Specify a stopping criterion. Note that the criterion has to match one of the
    # pretty printed result metrics from the results returned previously by
    # ``.train()``. Also note that -1100 is not a good episode return for
    # Pendulum-v1, we are using it here to shorten the experiment time.
    run_config=tune.RunConfig(
        stop={"env_runners/episode_return_mean": -1100.0}, # 停止条件 (Stopping Criterion)
    ),
)
# Run the Tuner and capture the results.
results = tuner.fit()

# 获取表现最好的那个试验的结果
best_result = results.get_best_result(
    metric="env_runners/episode_return_mean", # 依据哪个指标
    mode="max"                                # 越大越好
)

print("最佳学习率是:", best_result.config["lr"])
print("最佳回报是:", best_result.metrics["env_runners"]["episode_return_mean"])

# 获取对应的模型保存点
best_checkpoint = best_result.checkpoint


# 部署训练好的模型

from pathlib import Path
import gymnasium as gym
import numpy as np
import torch
from ray.rllib.core.rl_module import RLModule

# Create only the neural network (RLModule) from our algorithm checkpoint.
# See here (https://docs.ray.io/en/master/rllib/checkpoints.html)
# to learn more about checkpointing and the specific "path" used.
# 它只包含神经网络结构和权重，不包含优化器（Optimizer）、回放缓冲区（Replay Buffer）等训练时的重型组件。这使得它非常适合部署。
rl_module = RLModule.from_checkpoint(
    Path(best_checkpoint.path) # 使用前面最好的检查点模型，获取其本地路径
    / "learner_group"
    / "learner"
    / "rl_module"
    / "default_policy"
)

# Create the RL environment to test against (same as was used for training earlier).
env = gym.make("Pendulum-v1", render_mode="human")

episode_return = 0.0
done = False

# Reset the env to get the initial observation.
obs, info = env.reset()

while not done:
    # Uncomment this line to render the env.
    # env.render()

    # Compute the next action from a batch (B=1) of observations.
    obs_batch = torch.from_numpy(obs).unsqueeze(0)  # add batch B=1 dimension
    model_outputs = rl_module.forward_inference({"obs": obs_batch})

    # Extract the action distribution parameters from the output and dissolve batch dim.
    action_dist_params = model_outputs["action_dist_inputs"][0].numpy()

    # We have continuous actions -> take the mean (max likelihood).
    greedy_action = np.clip(
        action_dist_params[0:1],  # 0=mean, 1=log(stddev), [0:1]=use mean, but keep shape=(1,)
        a_min=env.action_space.low[0],
        a_max=env.action_space.high[0],
    )
    # For discrete actions, you should take the argmax over the logits:
    # greedy_action = np.argmax(action_dist_params)

    # Send the action to the environment for the next step.
    obs, reward, terminated, truncated, info = env.step(greedy_action)

    # Perform env-loop bookkeeping.
    episode_return += reward
    done = terminated or truncated

print(f"Reached episode return of {episode_return}.")