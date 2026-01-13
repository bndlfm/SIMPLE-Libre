# Operation Indices
OP_TRAIN = 0
OP_GARRISON = 1
OP_SWEEP = 2
OP_ASSAULT = 3

class CubaLibreEnv(gym.Env):
    metadata = {'render.modes': ['human']}

    def __init__(self, verbose=False, manual=False):
        super(CubaLibreEnv, self).__init__()
        self.name = 'cubalibre'
        self.n_players = 4
        self.factions_list = FACTIONS

        # Map Dimensions from your updated classes.py (IDs 0-12)
        self.num_spaces = 13
        self.space_feature_size = 12

        # Action Space: 4 Govt Ops * 13 Spaces
        # (We will ignore the other 4 ops for now to keep the test simple)
        self.num_ops = 8
        self.action_space = gym.spaces.Discrete(self.num_ops * self.num_spaces)

        # Observation Space
        self.obs_size = 9 + (self.num_spaces * self.space_feature_size)
        self.observation_space = gym.spaces.Box(
            low=0, high=50, shape=(self.obs_size,), dtype=np.float32
        )

    # ... [observation property remains the same] ...

    @property
    def observation(self):
        # (Same as previous turn, ensure it matches your shape)
        obs = []
        for p in self.players: obs.append(p.resources)
        for p in self.players: obs.append(1 if p.eligible else 0)
        obs.append(self.current_card.id if self.current_card else -1)
        for space in self.board.spaces:
            obs.append(space.alignment)
            obs.append(1 if space.support_active else 0)
            obs.append(space.terror)
            obs.append(1 if space.sabotage else 0)
            for count in space.pieces: obs.append(count)
        return np.array(obs, dtype=np.float32)

    @property
    def legal_actions(self):
        mask = np.zeros(self.action_space.n)
        player = self.players[self.current_player_num]

        # Only generating Logic for GOVT right now
        if player.name != "GOVT":
            return mask # Bots pass

        if not player.eligible or player.resources < 1:
            return mask

        # Loop through all spaces and enable valid Ops
        for space_id in range(self.num_spaces):
            space = self.board.spaces[space_id]

            # --- Op: TRAIN (0) ---
            # Rule: Place in City or where Base exists.
            # Govt Bases usually start in Cities, so for now check if City.
            if space.type == 0: # 0 is CITY
                action_idx = (OP_TRAIN * self.num_spaces) + space_id
                mask[action_idx] = 1

            # --- Op: GARRISON (1) ---
            # Rule: Move Police to any space with Police/Troops or adjacent to them.
            # Simplification: Allow on any space for now, let logic handle "no moves".
            action_idx = (OP_GARRISON * self.num_spaces) + space_id
            mask[action_idx] = 1

        return mask

    def step(self, action):
        reward = [0.0] * self.n_players
        done = False

        op_type = action // self.num_spaces
        space_idx = action % self.num_spaces
        player = self.players[self.current_player_num]

        if self.legal_actions[action] == 0:
            reward[self.current_player_num] = -1.0 # Invalid move penalty
        else:
            # Execute Logic
            if player.name == "GOVT":
                cost = 0
                if op_type == OP_TRAIN:
                    cost = self.op_train_govt(space_idx)
                elif op_type == OP_GARRISON:
                    cost = self.op_garrison_govt(space_idx)

                player.resources = max(0, player.resources - cost)
                player.eligible = False

        self.turns_taken += 1
        self.current_player_num = (self.current_player_num + 1) % self.n_players

        # Simple End Condition for Test
        if self.turns_taken >= 10:
            done = True

        self.done = done
        return self.observation, reward, done, {}

    # --- GOVERNMENT OPERATIONS ---

    def op_train_govt(self, space_id):
        """
        TRAIN: Place 6 Troops (or Police) in a City/Base.
        Cost: 2 Resources (simplified).
        """
        space = self.board.spaces[space_id]
        logger.debug(f"GOVT executes TRAIN in {space.name}")

        # Add 3 Troops (idx 0) and 3 Police (idx 1) for the test
        self.board.add_piece(space_id, 0, 0) # Troop
        self.board.add_piece(space_id, 0, 0) # Troop
        self.board.add_piece(space_id, 0, 0) # Troop
        self.board.add_piece(space_id, 0, 1) # Police
        self.board.add_piece(space_id, 0, 1) # Police
        self.board.add_piece(space_id, 0, 1) # Police

        return 2 # Return Cost

    def op_garrison_govt(self, space_id):
        """
        GARRISON: Move Police from adjacent spaces into target space.
        Cost: 0 if destination is City/EC, else 1.
        """
        target = self.board.spaces[space_id]
        moved_count = 0

        logger.debug(f"GOVT executes GARRISON into {target.name}")

        # Check all neighbors
        for adj_id in target.adj_ids:
            neighbor = self.board.spaces[adj_id]
            # Check for Police (Faction 0, Type 1 -> Index 1)
            police_count = neighbor.pieces[1]

            if police_count > 0:
                # Move 1 Police from neighbor to target
                self.board.remove_piece(adj_id, 0, 1)
                self.board.add_piece(space_id, 0, 1)
                moved_count += 1
                logger.debug(f" -> Moved police from {neighbor.name}")

        if moved_count == 0:
            logger.debug(" -> No police found in adjacent spaces to move.")

        return 0 # Simplified cost

    # ... [keep reset and render from previous turns] ...
    def reset(self):
        self.deck = Deck()
        self.deck_empty = False
        self.current_card = self.deck.draw()

        self.board = Board()
        self.players = []

        for i, name in enumerate(self.factions_list):
            f = Faction(i, name)
            f.resources = 20 if name == "GOVT" else (10 if name == "SYNDICATE" else 5)
            self.players.append(f)

        # Initial Setup (Havana has troops)
        self.board.add_piece(3, 0, 0) # Havana Troop
        self.board.add_piece(3, 0, 1) # Havana Police

        self.current_player_num = 0
        self.turns_taken = 0
        self.done = False
        return self.observation

    def render(self, mode='human', close=False):
        if close: return
        logger.debug(f"\n--- Turn {self.turns_taken} [{self.factions_list[self.current_player_num]}] Res:{self.players[self.current_player_num].resources} ---")
        out = f"{'Space':<18} | {'Govt(T/P)':<10} | {'Adjacency'}\n"
        out += "-" * 60 + "\n"
        for s in self.board.spaces:
            p = s.pieces
            g_str = f"{p[0]}/{p[1]}"
            adj_names = [self.board.spaces[i].name[:3] for i in s.adj_ids]
            out += f"{s.name:<18} | {g_str:<10} | {adj_names}\n"
        logger.debug(out)
