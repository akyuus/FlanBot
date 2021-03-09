# FlanBot
Stats bot for SA.

## Usage

### Get Indivs
`~gi <player_name>`

Example: `~gi alice`

### Get Pairs
`~gp <player1> <player2>`

Example: `~gp alice1 alice2`

### Get Bagger
`~gp <bagger_name>`

Example: `~gb bobby`

### Update Indivs
`~ui <opposing_team_tag> [<runner1>, ..., <runner4>] [<score1>, ... <score4>]`

Example: `~ui Rt [alice1, alice2, alice3, alice4] [90, 75, 81, 88]`

Note: You don't need to input 4 people strictly. 1 to 3 also work.

### Update Pairs
`~ui (W or L) [<player1>, <player2>, <player3>, <player4>, <player5>]`

Example: `~ui W [alice1, alice2, alice3, alice4, alice5]`

### Update Bagger
`~ub <bagger_name> <team> <shocks_pulled> <opponent_shocks_pulled>`

Example: `~ub alice Fw 7 4`