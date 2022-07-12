"""
This file is a part of the 'Unnamed' source code.
The source code is distributed under the MIT license.
"""

import abc
import logging
from typing import Optional

import pygame

from game.background import BackGroundEffect
from game.common import (HEIGHT, MAP_DIR, SAVE_DATA, SETTINGS_DIR, WIDTH,
                         EventInfo)
from game.enemy import MovingWall
from game.interactables.checkpoint import Checkpoint
from game.interactables.notes import Note
from game.interactables.portal import Portal
from game.interactables.sound_icon import SoundIcon
from game.items.grapple import Grapple
from game.player import Player
from game.states.enums import Dimensions, States
from game.utils import load_font, load_settings
from library.effects import ExplosionManager
from library.particles import ParticleManager, TextParticle
from library.sfx import SFXManager
from library.sprite.load import load_assets
from library.tilemap import TileLayerMap
from library.transition import FadeTransition
from library.ui.buttons import Button
from library.ui.camera import Camera

logger = logging.getLogger()


class InitLevelStage(abc.ABC):
    def __init__(self, switch_info: dict) -> None:
        """
        Initialize some attributes
        """

        self.switch_info = switch_info
        self.current_dimension = Dimensions.PARALLEL_DIMENSION
        self.latest_checkpoint = SAVE_DATA["latest_checkpoint"]

        self.camera = Camera(WIDTH, HEIGHT)
        self.sfx_manager = SFXManager("level")
        self.assets = load_assets("level")
        self.event_info = {"dt": 0}

        self.tilemap = TileLayerMap(MAP_DIR / "dimension_one.tmx")

        self.transition = FadeTransition(True, self.FADE_SPEED, (WIDTH, HEIGHT))
        self.next_state: Optional[States] = None

        self.settings = {
            enm.value: load_settings(SETTINGS_DIR / f"{enm.value}.json")
            for enm in Dimensions
        }

        self.dimensions_traveled = {self.current_dimension}
        self.enemies = set()
        self.portals = set()
        self.notes = set()
        self.particle_manager = ParticleManager(self.camera)

        self.checkpoints = {
            Checkpoint(pygame.Rect(obj.x, obj.y, obj.width, obj.height), self.particle_manager)
            for obj in self.tilemap.tilemap.get_layer_by_name("checkpoints")
        }

        self.player = Player(
            self.settings[self.current_dimension.value],
            self.latest_checkpoint,
            self.assets["dave_walk"],
            self.camera,
            self.particle_manager,
        )

    def update(*args, **kwargs):
        pass

    def draw(*args, **kwargs):
        pass


class RenderBackgroundStage(InitLevelStage):
    def __init__(self, switch_info: dict) -> None:
        super().__init__(switch_info)
        self.background_manager = BackGroundEffect(self.assets)

    def update(self):
        self.background_manager.update(self.event_info)

    def draw(self, screen):
        self.background_manager.draw(screen, self.camera, self.current_dimension)


class RenderCheckpointStage(RenderBackgroundStage):
    def draw(self, screen: pygame.Surface):
        super().draw(screen)

        for checkpoint in self.checkpoints:
            checkpoint.draw(screen)

class RenderPortalStage(RenderCheckpointStage):
    def draw(self, screen: pygame.Surface):
        super().draw(screen)

        for portal in self.portals:
            if portal.dimension_change:
                font = load_font(8)
                formatted_txt = portal.current_dimension.value.replace("_", " ").title()

                text_particle = TextParticle(
                    screen=screen,
                    image=font.render(
                        f"Switched to: {formatted_txt}", True, (218, 224, 234)
                    ),
                    pos=self.player.vec,
                    vel=(0, -1.5),
                    alpha_speed=3,
                    lifespan=80,
                )

                if portal.current_dimension not in self.dimensions_traveled:
                    self.dimensions_traveled.add(portal.current_dimension)

                    self.transition.fade_out_in(
                        on_finish=lambda: self.particle_manager.add(text_particle)
                    )
                else:
                    self.particle_manager.add(text_particle)

            portal.draw(screen, self.camera)


class RenderNoteStage(RenderPortalStage):
    def draw(self, screen):
        super().draw(screen)
        for note in self.notes:
            note.draw(screen, self.camera)


class RenderEnemyStage(RenderNoteStage):
    def draw(self, screen: pygame.Surface):
        super().draw(screen)
        for enemy in self.enemies:
            enemy.draw(self.event_info["dt"], screen, self.camera)


class TileStage(RenderEnemyStage):
    """
    Handles tilemap rendering
    """

    def __init__(self, switch_info: dict) -> None:
        super().__init__(switch_info)
        # self.tilemap = TileLayerMap(MAP_DIR / f"{self.current_dimension.value}.tmx"

        self.map_surf = self.tilemap.make_map()

        for enemy_obj in self.tilemap.tilemap.get_layer_by_name("enemies"):
            if enemy_obj.name == "moving_wall":
                self.enemies.add(
                    MovingWall(
                        self.settings[self.current_dimension.value],
                        enemy_obj,
                        self.assets,
                    )
                )

        self.tilesets = {enm: self.assets[enm.value] for enm in Dimensions}

    def draw(self, screen: pygame.Surface):
        super().draw(screen)
        screen.blit(self.map_surf, self.camera.apply((0, 0)))


"""class ItemStage(TileStage):
    def __init__(self, switch_info: dict) -> None:
        super().__init__(switch_info)

        self.grapple = Grapple(self.player, self.camera)
    
    def draw(self, screen):
        super().draw(screen)
        self.grapple.draw(screen)
    
    def update(self, event_info: EventInfo):
        self.grapple.update(event_info, self.tilemap)"""


class PlayerStage(TileStage):
    """
    Handle player related actions
    """

    def __init__(self, switch_info: dict) -> None:
        super().__init__(switch_info)

        # self.player = Player(
        #     self.settings[self.current_dimension.value], self.assets["dave_walk"]
        # )

    def update(self, event_info: EventInfo):
        super().update()

        self.player.update(event_info, self.tilemap, self.enemies)
        self.event_info = event_info

        # Temporary checking here
        if self.player.y > 2000:
            self.player.alive = False
            SAVE_DATA["latest_checkpoint"] = self.latest_checkpoint

    def draw(self, screen: pygame.Surface):
        super().draw(screen)
        self.player.draw(screen, self.camera)


class ItemStage(PlayerStage):
    def __init__(self, switch_info: dict) -> None:
        super().__init__(switch_info)

    def draw(self, screen):
        super().draw(screen)
        # self.grapple.draw(screen)

    def update(self, event_info: EventInfo):
        super().update(event_info)
        # self.grapple.update(event_info, self.tilemap, self.enemies)


class SpecialTileStage(ItemStage):
    def __init__(self, switch_info: dict) -> None:
        super().__init__(switch_info)

    def update(self, event_info: EventInfo):
        super().update(event_info)

        for special_tiles in self.tilemap.special_tiles.values():
            special_tiles.update(self.player)


class EnemyStage(SpecialTileStage):
    def update(self, event_info: EventInfo):
        super().update(event_info)

        for enemy in self.enemies:
            enemy.update(event_info, self.tilemap, self.player)


class CheckpointStage(EnemyStage):
    def __init__(self, switch_info: dict) -> None:
        super().__init__(switch_info)
    
    def update(self, event_info: EventInfo):
        super().update(event_info)
        for checkpoint in self.checkpoints:
            if not checkpoint.text_spawned and checkpoint.rect.colliderect(self.player.rect):
                self.latest_checkpoint = checkpoint.rect.midbottom
            
            checkpoint.update(self.player.rect)


class NoteStage(CheckpointStage):
    def __init__(self, switch_info: dict) -> None:
        super().__init__(switch_info)
        self.notes = {
            Note(self.assets["note"], (obj.x, obj.y), obj.properties["text"])
            for obj in self.tilemap.tilemap.get_layer_by_name("notes")
        }

    def update(self, event_info: EventInfo):
        super().update(event_info)
        for note in self.notes:
            note.update(event_info, self.player.rect)


class PortalStage(NoteStage):
    def __init__(self, switch_info: dict) -> None:
        super().__init__(switch_info)
        self.unlocked_dimensions = [
            Dimensions.PARALLEL_DIMENSION,
            Dimensions.VOLCANIC_DIMENSION,
        ]

        for portal_obj in self.tilemap.tilemap.get_layer_by_name("portals"):
            if portal_obj.name == "portal":
                self.portals.add(
                    Portal(portal_obj, self.unlocked_dimensions, self.assets["portal"])
                )

    def update(self, event_info: EventInfo):
        super().update(event_info)

        for portal in self.portals:
            # if we aren't changing the dimension,
            # we have to reset portal's dimension to the current one
            if not portal.dimension_change:
                portal.current_dimension = self.current_dimension
            # otherwise (if we're switching dimension)
            else:
                logger.info(f"Changed dimension to: {portal.current_dimension}")

                self.current_dimension = portal.current_dimension
                self.map_surf = self.tilemap.make_map(
                    self.tilesets[self.current_dimension]
                )

                # change player's settings
                self.player.change_settings(self.settings[self.current_dimension.value])
                # change enemy settings
                for enemy in self.enemies:
                    enemy.change_settings(self.settings[self.current_dimension.value])

            portal.update(self.player, event_info)

        # Unlocking dimensions
        for event in event_info["events"]:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_5:
                for dimension in Dimensions:
                    if dimension not in self.unlocked_dimensions:
                        self.unlocked_dimensions.append(dimension)
                        break

                for portal in self.portals:
                    portal.unlock_dimension(self.unlocked_dimensions)


class CameraStage(PortalStage):
    def update(self, event_info: EventInfo):
        super().update(event_info)

        self.camera.adjust_to(event_info["dt"], self.player.rect)


class UIStage(CameraStage):
    """
    Handles buttons
    """

    def __init__(self, switch_info: dict) -> None:
        super().__init__(switch_info)
        self.buttons = ()

    def update(self, event_info: EventInfo):
        """
        Update the Button state

        Parameters:
            event_info: Information on the window events
        """
        super().update(event_info)
        for button in self.buttons:
            button.update(event_info["mouse_pos"], event_info["mouse_press"])

        self.particle_manager.update(event_info)

    def draw(self, screen: pygame.Surface):
        """
        Draw the Button state

        Parameters:
            screen: pygame.Surface to draw on
        """
        super().draw(screen)
        for button in self.buttons:
            button.draw(screen)
        self.particle_manager.draw()


class SFXStage(UIStage):
    def __init__(self, switch_info: dict) -> None:
        super().__init__(switch_info)
        stub_rect = pygame.Rect(0, 0, 16, 16)
        stub_rect.topright = pygame.Surface((WIDTH, HEIGHT)).get_rect().topright
        stub_rect.topright = (stub_rect.topright[0] - 32, stub_rect.topright[1] + 16)
        self.sound_icon = SoundIcon(
            self.sfx_manager, self.assets, center_pos=stub_rect.center
        )

        self.sfx_manager.set_volume(SAVE_DATA["last_volume"] * 100)
        self.sound_icon.slider.value = (
            SAVE_DATA["last_volume"] * self.sound_icon.slider.max_value
        )

    def update(self, event_info: EventInfo):
        super().update(event_info)
        self.sound_icon.update(event_info)

    def draw(self, screen: pygame.Surface):
        super().draw(screen)
        self.sound_icon.draw(screen)


class ExplosionStage(SFXStage):
    def __init__(self, switch_info: dict) -> None:
        super().__init__(switch_info)
        self.explosion_manager = ExplosionManager("fire")

    def update(self, event_info: EventInfo) -> None:
        super().update(event_info)
        self.explosion_manager.update(event_info["dt"])

        # for event in event_info["events"]:
        #     if event.type == pygame.MOUSEBUTTONDOWN:

    def draw(self, screen: pygame.Surface):
        super().draw(screen)
        self.explosion_manager.draw(screen)


class TransitionStage(ExplosionStage):
    """
    Handles game state transitions
    """

    FADE_SPEED = 4

    def __init__(self, switch_info: dict) -> None:
        super().__init__(switch_info)

        # Store any information needed to be passed
        # on to the next state
        self.switch_info = {}

    def update(self, event_info: EventInfo):
        super().update(event_info)
        """
        Update the transition stage

        Parameters:
            event_info: Information on the window events
        """
        self.transition.update(event_info["dt"])
        if not self.player.alive:
            self.transition.fade_in = False
            if self.transition.event:
                self.next_state = States.MAIN_MENU

    def draw(self, screen: pygame.Surface) -> None:
        super().draw(screen)
        self.transition.draw(screen)


class Level(TransitionStage):
    """
    Final element of stages chain
    """

    def update(self, event_info: EventInfo):
        """
        Update the Level state

        Parameters:
            event_info: Information on the window events
        """
        super().update(event_info)

    def draw(self, screen: pygame.Surface):
        """
        Draw the Level state

        Parameters:
            screen: pygame.Surface to draw on
        """
        super().draw(screen)
