import time
import pygame
import pymunk
import pymunk.pygame_util
from streamerbot import start_client, get_new_messages
from config import config
from atlas import create_texture_atlas
from pathlib import Path
from chunk import get_block, clean_chunks, delete_block, chunks
from constants import BLOCK_SCALE_FACTOR, BLOCK_SIZE, CHUNK_HEIGHT, CHUNK_WIDTH, INTERNAL_HEIGHT, INTERNAL_WIDTH, FRAMERATE
from pickaxe import Pickaxe
from camera import Camera
from sound import SoundManager
from tnt import Tnt, MegaTnt
import random
from hud import Hud
from collections import deque

# Track key states
key_t_pressed = False
key_m_pressed = False
key_s_pressed = False
key_i_pressed = False
key_b_pressed = False
key_f_pressed = False
key_l_pressed = False

# Queues for chat
tnt_queue = deque()
tnt_superchat_queue = deque()
fast_slow_queue = deque()
big_queue = deque()
pickaxe_queue = deque()
mega_tnt_queue = deque()
pending_tnt_spawns = deque()

def game():
    start_client()
    window_width = int(INTERNAL_WIDTH / 2)
    window_height = int(INTERNAL_HEIGHT / 2)

    # Initialize pygame
    pygame.init()
    clock = pygame.time.Clock()

    # Pymunk physics
    space = pymunk.Space()
    space.gravity = (0, 1000)  # (x, y) - down is positive y

    # Create a resizable window
    screen_size = (window_width, window_height)
    screen = pygame.display.set_mode(screen_size, pygame.RESIZABLE)
    scaled_surface = pygame.Surface(screen_size).convert()
    pygame.display.set_caption("Falling Pickaxe")
    # set icon
    icon = pygame.image.load(Path(__file__).parent.parent / "src/assets/pickaxe" / "diamond_pickaxe.png")
    pygame.display.set_icon(icon)

    # Create an internal surface with fixed resolution
    internal_surface = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT))

    # Load texture atlas
    assets_dir = Path(__file__).parent.parent / "src/assets"
    (texture_atlas, atlas_items) = create_texture_atlas(assets_dir)

    # Load background
    background_image = pygame.image.load(assets_dir / "background.png")
    background_scale_factor = 1.5
    background_width = int(background_image.get_width() * background_scale_factor)
    background_height = int(background_image.get_height() * background_scale_factor)
    background_image = pygame.transform.scale(background_image, (background_width, background_height))

    # Scale the entire texture atlas
    texture_atlas = pygame.transform.scale(texture_atlas,
                                        (texture_atlas.get_width() * BLOCK_SCALE_FACTOR,
                                        texture_atlas.get_height() * BLOCK_SCALE_FACTOR))

    for category in atlas_items:
        for item in atlas_items[category]:
            x, y, w, h = atlas_items[category][item]
            atlas_items[category][item] = (x * BLOCK_SCALE_FACTOR, y * BLOCK_SCALE_FACTOR, w * BLOCK_SCALE_FACTOR, h * BLOCK_SCALE_FACTOR)

    #sounds
    sound_manager = SoundManager()

    sound_manager.load_sound("tnt", assets_dir / "sounds" / "tnt.mp3", 0.3)
    sound_manager.load_sound("stone1", assets_dir / "sounds" / "stone1.wav", 0.5)
    sound_manager.load_sound("stone2", assets_dir / "sounds" / "stone2.wav", 0.5)
    sound_manager.load_sound("stone3", assets_dir / "sounds" / "stone3.wav", 0.5)
    sound_manager.load_sound("stone4", assets_dir / "sounds" / "stone4.wav", 0.5)
    sound_manager.load_sound("grass1", assets_dir / "sounds" / "grass1.wav", 0.1)
    sound_manager.load_sound("grass2", assets_dir / "sounds" / "grass2.wav", 0.1)
    sound_manager.load_sound("grass3", assets_dir / "sounds" / "grass3.wav", 0.1)
    sound_manager.load_sound("grass4", assets_dir / "sounds" / "grass4.wav", 0.1)

    # Pickaxe
    pickaxe = Pickaxe(space, INTERNAL_WIDTH // 2, INTERNAL_HEIGHT // 2, texture_atlas.subsurface(atlas_items["pickaxe"]["wooden_pickaxe"]), sound_manager)

    # TNT
    last_tnt_spawn = pygame.time.get_ticks()
    tnt_spawn_interval = 1000 * random.uniform(config["TNT_SPAWN_INTERVAL_SECONDS_MIN"], config["TNT_SPAWN_INTERVAL_SECONDS_MAX"])
    tnt_list = []  # List to keep track of spawned TNT objects
    last_staggered_tnt_spawn = pygame.time.get_ticks()

    # Random Pickaxe
    last_random_pickaxe = pygame.time.get_ticks()
    random_pickaxe_interval = 1000 * random.uniform(config["RANDOM_PICKAXE_INTERVAL_SECONDS_MIN"], config["RANDOM_PICKAXE_INTERVAL_SECONDS_MAX"])

    # Pickaxe enlargement
    last_enlarge = pygame.time.get_ticks()
    enlarge_interval = 1000 * random.uniform(config["PICKAXE_ENLARGE_INTERVAL_SECONDS_MIN"], config["PICKAXE_ENLARGE_INTERVAL_SECONDS_MAX"])
    enlarge_duration = 1000 * config["PICKAXE_ENLARGE_DURATION_SECONDS"]

    # Fast slow
    fast_slow_active = False
    fast_slow = random.choice(["Fast", "Slow"])
    fast_slow_interval = 1000 * random.uniform(config["FAST_SLOW_INTERVAL_SECONDS_MIN"], config["FAST_SLOW_INTERVAL_SECONDS_MAX"])
    last_fast_slow = pygame.time.get_ticks()

    # Camera
    camera = Camera()

    # HUD
    hud = Hud(texture_atlas, atlas_items)

    # Explosions
    explosions = []

    # Youtube

    # Save progress interval
    save_progress_interval = 1000 * config["SAVE_PROGRESS_INTERVAL_SECONDS"]
    last_save_progress = pygame.time.get_ticks()

    # Youtupe chat queues

    # Main loop
    running = True
    user_quit = False
    while running:
        # ++++++++++++++++++  EVENTS ++++++++++++++++++
        for event in pygame.event.get():
            if event.type == pygame.QUIT:  # Close window event
                running = False
                user_quit = True
            elif event.type == pygame.VIDEORESIZE:  # Window resize event
                new_width, new_height = event.w, event.h

                # Maintain 4:3 aspect ratio
                if new_width / 4 > new_height / 3:
                    new_width = int(new_height * (4 / 3))
                else:
                    new_height = int(new_width * (3 / 4))

                window_width, window_height = new_width, new_height
                screen = pygame.display.set_mode((window_width, window_height), pygame.RESIZABLE)
                scaled_surface = pygame.Surface((window_width, window_height)).convert()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    pickaxe_queue.append(("TestUser", "wooden_pickaxe"))
                elif event.key == pygame.K_2:
                    pickaxe_queue.append(("TestUser", "stone_pickaxe"))
                elif event.key == pygame.K_3:
                    pickaxe_queue.append(("TestUser", "iron_pickaxe"))
                elif event.key == pygame.K_4:
                    pickaxe_queue.append(("TestUser", "golden_pickaxe"))
                elif event.key == pygame.K_5:
                    pickaxe_queue.append(("TestUser", "diamond_pickaxe"))
                elif event.key == pygame.K_6:
                    pickaxe_queue.append(("TestUser", "netherite_pickaxe"))

        # ++++++++++++++++++  UPDATE ++++++++++++++++++
        # Determine which chunks are visible
        # Update physics

        dt_ms = clock.get_time()
        current_time = pygame.time.get_ticks()

        step_speed = 1 / FRAMERATE  # Fixed time step for physics simulation
        if fast_slow_active and fast_slow == "Fast":
            step_speed = 1 / (FRAMERATE / 2)
        elif fast_slow_active and fast_slow == "Slow":
            step_speed = 1 / (FRAMERATE * 2)

        space.step(step_speed)

        start_chunk_y = int(pickaxe.body.position.y // (CHUNK_HEIGHT * BLOCK_SIZE) - 1) - 1
        end_chunk_y = int(pickaxe.body.position.y + INTERNAL_HEIGHT) // (CHUNK_HEIGHT * BLOCK_SIZE)  + 1

        # Update pickaxe
        pickaxe.update(current_time)

        # Update camera
        camera.update(pickaxe.body.position.y)

        # ++++++++++++++++++  DRAWING ++++++++++++++++++
        # Clear the internal surface
        screen.fill((0, 0, 0))

        # Fill internal surface with the background
        internal_surface.blit(background_image, ((INTERNAL_WIDTH - background_width) // 2, (INTERNAL_HEIGHT - background_height) // 2))

        # Check if it's time to spawn a new TNT (regular random spawn)
        if (not config["CHAT_CONTROL"] or (not tnt_queue and not tnt_superchat_queue and not mega_tnt_queue)) and current_time - last_tnt_spawn >= tnt_spawn_interval:
             # Example: spawn TNT at position (400, 300) with a given texture
             new_tnt = Tnt(space, pickaxe.body.position.x, pickaxe.body.position.y - 100,
               texture_atlas, atlas_items, sound_manager)
             tnt_list.append(new_tnt)
             last_tnt_spawn = current_time
             # New random interval for the next TNT spawn
             tnt_spawn_interval = 1000 * random.uniform(config["TNT_SPAWN_INTERVAL_SECONDS_MIN"], config["TNT_SPAWN_INTERVAL_SECONDS_MAX"])

        # Check if it's time to change the pickaxe (random)
        if (not config["CHAT_CONTROL"] or not pickaxe_queue) and current_time - last_random_pickaxe >= random_pickaxe_interval:
            pickaxe.random_pickaxe(texture_atlas, atlas_items)
            last_random_pickaxe = current_time
            # New random interval for the next pickaxe change
            random_pickaxe_interval = 1000 * random.uniform(config["RANDOM_PICKAXE_INTERVAL_SECONDS_MIN"], config["RANDOM_PICKAXE_INTERVAL_SECONDS_MAX"])

        # Check if it's time for pickaxe enlargement (random)
        if (not config["CHAT_CONTROL"] or not big_queue) and current_time - last_enlarge >= enlarge_interval:
            pickaxe.enlarge(enlarge_duration)
            last_enlarge = current_time + enlarge_duration
            # New random interval for the next enlargement
            enlarge_interval = 1000 * random.uniform(config["PICKAXE_ENLARGE_INTERVAL_SECONDS_MIN"], config["PICKAXE_ENLARGE_INTERVAL_SECONDS_MAX"])

        # Check if it's time to change speed (random)
        if (not config["CHAT_CONTROL"] or not fast_slow_queue) and current_time - last_fast_slow >= fast_slow_interval and not fast_slow_active:
            # Randomly choose between "fast" and "slow"
            fast_slow = random.choice(["Fast", "Slow"])
            print("Changing speed to:", fast_slow)
            fast_slow_active = True
            last_fast_slow = current_time
            # New random interval for the next fast/slow spawn
            fast_slow_interval = 1000 * random.uniform(config["FAST_SLOW_INTERVAL_SECONDS_MIN"], config["FAST_SLOW_INTERVAL_SECONDS_MAX"])
        elif current_time - last_fast_slow >= (1000 * config["FAST_SLOW_DURATION_SECONDS"]) and fast_slow_active:
            fast_slow_active = False
            last_fast_slow = current_time

        # Update all TNTs
        for tnt in tnt_list:
            tnt.update(tnt_list, explosions, camera, current_time)

        # Poll Streamer.bot
        if config["CHAT_CONTROL"] == True:
            new_messages = get_new_messages()

            for message in new_messages:
                author = message["author"]
                text = message["message"]
                is_subscriber = message.get("is_subscriber", False)
                text_lower = text.lower()

                # Check for new subscriber (trigger 10 TNTs)
                if is_subscriber:
                    # Reuse tnt_superchat_queue for subscribers
                    tnt_superchat_queue.append((author, "subscriber"))
                    print(f"Added {author} to Subscriber TNT queue")
                    continue # Skip command processing for sub events

                # Check for "tnt" command (add author to regular tnt_queue) - Only English "tnt"
                if "megatnt" in text_lower:
                    mega_tnt_queue.append(author)
                    print(f"Added {author} to MegaTNT queue")
                elif "tnt" in text_lower:
                    tnt_queue.append(author)
                    print(f"Added {author} to regular TNT queue")

                if "fast" in text_lower:
                    fast_slow_queue.append((author, "Fast"))
                    print(f"Added {author} to Fast/Slow queue (Fast)")
                elif "slow" in text_lower:
                    fast_slow_queue.append((author, "Slow"))
                    print(f"Added {author} to Fast/Slow queue (Slow)")

                if "big" in text_lower:
                    big_queue.append(author)
                    print(f"Added {author} to Big queue")

                # Check for pickaxe commands (add author and pickaxe type to pickaxe_queue)
                if "wood" in text_lower:
                    pickaxe_queue.append((author, "wooden_pickaxe"))
                    print(f"Added {author} to Pickaxe queue (wooden_pickaxe)")
                elif "stone" in text_lower:
                    pickaxe_queue.append((author, "stone_pickaxe"))
                    print(f"Added {author} to Pickaxe queue (stone_pickaxe)")
                elif "iron" in text_lower:
                    pickaxe_queue.append((author, "iron_pickaxe"))
                    print(f"Added {author} to Pickaxe queue (iron_pickaxe)")
                elif "gold" in text_lower:
                    pickaxe_queue.append((author, "golden_pickaxe"))
                    print(f"Added {author} to Pickaxe queue (golden_pickaxe)")
                elif "diamond" in text_lower:
                    pickaxe_queue.append((author, "diamond_pickaxe"))
                    print(f"Added {author} to Pickaxe queue (diamond_pickaxe)")
                elif "netherite" in text_lower:
                    pickaxe_queue.append((author, "netherite_pickaxe"))
                    print(f"Added {author} to Pickaxe queue (netherite_pickaxe)")

        # Process chat queues
        if config["CHAT_CONTROL"]:
            # Handle regular TNT from chat command
            while tnt_queue:
                author = tnt_queue.popleft()
                print(f"Spawning regular TNT for {author} (from chat command)")
                new_tnt = Tnt(space, pickaxe.body.position.x, pickaxe.body.position.y - 100,
                             texture_atlas, atlas_items, sound_manager, owner_name=author)
                tnt_list.append(new_tnt)
                last_tnt_spawn = current_time

            # Handle MegaTNT
            while mega_tnt_queue:
                author = mega_tnt_queue.popleft()
                print(f"Spawning MegaTNT for {author}")
                new_megatnt = MegaTnt(space, pickaxe.body.position.x, pickaxe.body.position.y - 100,
                      texture_atlas, atlas_items, sound_manager, owner_name=author)
                tnt_list.append(new_megatnt)
                last_tnt_spawn = current_time

            # Handle Subscriber TNT
            while tnt_superchat_queue:
                author, text = tnt_superchat_queue.popleft()
                print(f"Queuing 10 TNTs for {author} (New Subscriber)")
                hud.show_thank_you(f"Thanks for subscribing, {author}!", current_time)
                for _ in range(config["TNT_AMOUNT_ON_SUPERCHAT"]):
                    pending_tnt_spawns.append(author)

            # Handle Fast/Slow command
            while fast_slow_queue:
                author, q_fast_slow = fast_slow_queue.popleft()
                print(f"Changing speed for {author} to {q_fast_slow}")
                fast_slow_active = True
                last_fast_slow = current_time
                fast_slow = q_fast_slow
                fast_slow_interval = 1000 * random.uniform(config["FAST_SLOW_INTERVAL_SECONDS_MIN"], config["FAST_SLOW_INTERVAL_SECONDS_MAX"])
                
                # Add juice timers
                if fast_slow == "Fast":
                    pickaxe.fast_timer = current_time
                elif fast_slow == "Slow":
                    pickaxe.slow_timer = current_time

            # Handle Big pickaxe command
            while big_queue:
                author = big_queue.popleft()
                print(f"Making pickaxe big for {author}")
                pickaxe.enlarge(enlarge_duration)
                camera.shake(30, 15)  # Massive screen shake for BIG
                last_enlarge = current_time + enlarge_duration
                enlarge_interval = 1000 * random.uniform(config["PICKAXE_ENLARGE_INTERVAL_SECONDS_MIN"], config["PICKAXE_ENLARGE_INTERVAL_SECONDS_MAX"])

            # Handle Pickaxe type command
            while pickaxe_queue:
                author, pickaxe_type = pickaxe_queue.popleft()
                print(f"Changing pickaxe for {author} to {pickaxe_type}")
                pickaxe.pickaxe(pickaxe_type, texture_atlas, atlas_items)
                last_random_pickaxe = current_time
                random_pickaxe_interval = 1000 * random.uniform(config["RANDOM_PICKAXE_INTERVAL_SECONDS_MIN"], config["RANDOM_PICKAXE_INTERVAL_SECONDS_MAX"])


        # Process pending TNT spawns (staggered)
        if pending_tnt_spawns and current_time - last_staggered_tnt_spawn >= 100:
            author = pending_tnt_spawns.popleft()
            new_tnt = Tnt(space, pickaxe.body.position.x, pickaxe.body.position.y - 100, texture_atlas, atlas_items, sound_manager, owner_name=author)
            tnt_list.append(new_tnt)
            last_staggered_tnt_spawn = current_time

        # Delete chunks
        clean_chunks(start_chunk_y, space)

        # Draw blocks in visible chunks
        for chunk_x in range(-1, 2):
            for chunk_y in range(start_chunk_y, end_chunk_y):
                for y in range(CHUNK_HEIGHT):
                    for x in range(CHUNK_WIDTH):
                        block = get_block(chunk_x, chunk_y, x, y, texture_atlas, atlas_items, space)

                        if block == None:
                            continue

                        block.update(space, hud, current_time)
                        block.draw(internal_surface, camera)

        # Draw pickaxe
        pickaxe.draw(internal_surface, camera)

        # Draw TNT
        for tnt in tnt_list:
            tnt.draw(internal_surface, camera)

        # Draw particles
        for explosion in explosions:
            explosion.update(dt_ms)
            explosion.draw(internal_surface, camera)

        # Optionally, remove explosions that have no particles left:
        explosions = [e for e in explosions if e.particles]

        # Draw HUD
        hud.draw(internal_surface, pickaxe.body.position.y, fast_slow_active, fast_slow)

        # Scale internal surface to fit the resized window
        pygame.transform.scale(internal_surface, (window_width, window_height), scaled_surface)
        screen.blit(scaled_surface, (0, 0))

        # Save progress
        if current_time - last_save_progress >= save_progress_interval:
            # Save the game state or progress here
            print("Saving progress...")
            last_save_progress = current_time
            # Save progress to logs folder
            log_dir = Path(__file__).parent.parent / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            with open(log_dir / "progress.txt", "a+") as f:
                f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')} | ")
                f.write(f"Y: {-int(pickaxe.body.position.y // BLOCK_SIZE)} ")
                f.write(f"coal: {hud.amounts['coal']} ")
                f.write(f"iron: {hud.amounts['iron_ingot']} ")
                f.write(f"gold: {hud.amounts['gold_ingot']} ")
                f.write(f"copper: {hud.amounts['copper_ingot']} ")
                f.write(f"redstone: {hud.amounts['redstone']} ")
                f.write(f"lapis: {hud.amounts['lapis_lazuli']} ")
                f.write(f"diamond: {hud.amounts['diamond']} ")
                f.write(f"emerald: {hud.amounts['emerald']} \n")

        # Update the display
        pygame.display.flip()
        clock.tick(FRAMERATE)  # Cap the frame rate

        # Inside the main loop
        keys = pygame.key.get_pressed()

        # Handle TNT spawn (key T)
        if keys[pygame.K_t]:
            if not key_t_pressed:  # Only spawn if the key was not pressed in the previous frame
                new_tnt = Tnt(space, pickaxe.body.position.x, pickaxe.body.position.y - 100,
                            texture_atlas, atlas_items, sound_manager)
                tnt_list.append(new_tnt)
                last_tnt_spawn = current_time
                # New random interval for the next TNT spawn
                tnt_spawn_interval = 1000 * random.uniform(config["TNT_SPAWN_INTERVAL_SECONDS_MIN"], config["TNT_SPAWN_INTERVAL_SECONDS_MAX"])
            key_t_pressed = True
        else:
            key_t_pressed = False  # Reset the flag when the key is released

        # Handle MegaTNT spawn (key M)
        if keys[pygame.K_m]:
            if not key_m_pressed:  # Only spawn if the key was not pressed in the previous frame
                new_megatnt = MegaTnt(space, pickaxe.body.position.x, pickaxe.body.position.y - 100,
                                    texture_atlas, atlas_items, sound_manager)
                tnt_list.append(new_megatnt)
                last_tnt_spawn = current_time
                # New random interval for the next TNT spawn
                tnt_spawn_interval = 1000 * random.uniform(config["TNT_SPAWN_INTERVAL_SECONDS_MIN"], config["TNT_SPAWN_INTERVAL_SECONDS_MAX"])
            key_m_pressed = True
        else:
            key_m_pressed = False  # Reset the flag when the key is released

        # Handle testing Subscriber (key S)
        if keys[pygame.K_s]:
            if not key_s_pressed:
                tnt_superchat_queue.append(("TestUser", "subscriber"))
                print("Simulating new subscriber via S key")
            key_s_pressed = True
        else:
            key_s_pressed = False

        if keys[pygame.K_i]:
            if not key_i_pressed:
                pickaxe_queue.append(("TestUser", "iron_pickaxe"))
            key_i_pressed = True
        else:
            key_i_pressed = False
            
        if keys[pygame.K_b]:
            if not key_b_pressed:
                big_queue.append("TestUser")
            key_b_pressed = True
        else:
            key_b_pressed = False
            
        if keys[pygame.K_f]:
            if not key_f_pressed:
                fast_slow_queue.append(("TestUser", "Fast"))
            key_f_pressed = True
        else:
            key_f_pressed = False
            
        if keys[pygame.K_l]:
            if not key_l_pressed:
                fast_slow_queue.append(("TestUser", "Slow"))
            key_l_pressed = True
        else:
            key_l_pressed = False

    # Quit pygame properly
    pygame.quit()

    # Return exit code: 0 for user quit (close window), 1 for crash/error
    if user_quit:
        import sys
        sys.exit(0)  # Normal exit - user closed window
    else:
        import sys
        sys.exit(1)  # Abnormal exit - game crashed or error

game()
