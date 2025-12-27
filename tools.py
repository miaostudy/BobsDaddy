

def print_train_and_eval_status(result):
    """
    全能打印函数：同时显示训练进度和评估结果 (New API Stack 专用)
    """
    # --- 1. 基础信息 ---
    iteration = result.get('training_iteration', 0)
    time_total = result.get('time_total_s', 0)

    print(f"\n{'=' * 20} 📅 迭代 (Iteration): {iteration} | ⏱️ 总耗时: {time_total:.1f}s {'=' * 20}")

    # --- 2. 训练集表现 (Training) ---
    # 这里的 env_runners 是训练期间的数据
    train_runners = result.get('env_runners', {})
    train_return = train_runners.get('episode_return_mean', float('nan'))
    train_ep_len = train_runners.get('episode_len_mean', 0)

    print(f"🏋️  [训练集表现] (Training)")
    print(f"    • 平均回报 : {train_return:.2f}")
    print(f"    • 平均步数 : {train_ep_len:.1f}")

    # --- 3. 评估集表现 (Evaluation) ---
    # 检查是否存在 evaluation 字段
    if 'evaluation' in result and result['evaluation']:
        # 注意：评估的具体指标通常也在下一级的 'env_runners' 里
        eval_runners = result['evaluation'].get('env_runners', {})

        eval_return = eval_runners.get('episode_return_mean', float('nan'))
        eval_max = eval_runners.get('episode_return_max', float('nan'))
        eval_min = eval_runners.get('episode_return_min', float('nan'))
        eval_len = eval_runners.get('episode_len_mean', 0)

        print(f"📝  [评估集表现] (Evaluation - 不带噪声的测试)")
        print(f"    • 平均回报 : {eval_return:.2f}")
        print(f"    • 最佳表现 : {eval_max:.2f}")
        print(f"    • 最差表现 : {eval_min:.2f}")
        print(f"    • 平均步数 : {eval_len:.1f}")
    else:
        print(f"📝  [评估集表现] (本轮未执行评估)")

    # --- 4. 模型内部状态 (可选) ---
    policy_stats = result.get('learners', {}).get('default_policy', {})
    entropy = policy_stats.get('entropy', float('nan'))
    vf_loss = policy_stats.get('vf_loss', float('nan'))
    policy_loss = policy_stats.get('policy_loss', float('nan'))
    print(f"🧠  [模型内部]")
    print(f"    • 策略熵   : {entropy:.4f}")
    print(f"   • 价值损失 (VF Loss)     : {vf_loss:.4f} (Critic误差)")
    print(f"   • 策略损失 (Policy Loss) : {policy_loss:.4f} (Actor更新幅度)")