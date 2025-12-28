# TODO
- [ ] 自动更新卡片信息
- [ ] 补丁解析

# 自动爬取数据
## 运行命令
```shell
bash ./scripts/update_everything.sh
```
## 数据格式
以`json`格式保存。

英雄: 
```
{   
    id: int 标识卡牌的唯一id
    type: enum ['hero 英雄', 'minion 随从', 'spell 法术', 'task 任务', 'award 奖励', 'mutation 异变', 'accessories 饰品', 'timeWarp 时光扭曲']
    name: string 卡牌名
    description: [string] [技能描述]
    addiction: [int] [衍生卡牌id]
    used: True/ False 当前版本是否使用该卡牌
}
```
随从：
```
{   
    id: int 标识卡牌的唯一id
    type: enum ['hero 英雄', 'minion 随从', 'spell 法术', 'task 任务', 'award 奖励', 'mutation 异变', 'accessories 饰品', 'timeWarp 时光扭曲']
    race: [string] 种族名
    leval: int 星级
    name: string 卡牌名
    description: string 牌面描述
    attack: int 攻击力
    health: int 血量
    addiction: [int] [衍生卡牌id]
    golden：
    {
        name
        description
        attack
        health
    }
    used: True/ False 当前版本是否使用该卡牌
}
``` 

文件结构：
```
-asserts 数据文件夹
    -imgs 按卡牌类型存储牌面图片
        -hero
            - 1.png
    ....
    -jsons 按卡牌类型存储卡牌信息
        -heros.json
        -minions.json
    ....
```


## 类设计
可以实现成：父类是各个类型的卡牌共有的属性，子类是各种卡牌。