from __future__ import annotations

import logging
from dataclasses import dataclass

import geopandas as gpd
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProfileShareThresholds:
    """Thresholds for interpreting the share of profile objects (in percent)."""
    low: float = 10.0
    weak: float = 15.0
    medium: float = 30.0
    good: float = 70.0
    high: float = 90.0


class _ColumnsValidator:
    """Validates presence of required columns in input dataframe."""

    def ensure(self, df: pd.DataFrame, required: list[str]) -> None:
        """Raise ValueError if any required columns are missing."""
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(missing)}")


class InterpretationService:
    def __init__(
        self,
        thresholds: ProfileShareThresholds = ProfileShareThresholds(),
        validator: _ColumnsValidator | None = None,
    ) -> None:
        """Create service with injected thresholds and validator (test-friendly)."""
        self._t = thresholds
        self._validator = validator or _ColumnsValidator()

    @staticmethod
    def _to_numeric_series(df: pd.DataFrame, column: str) -> pd.Series:
        """Convert a dataframe column to numeric series with NaN on errors."""
        return pd.to_numeric(df[column], errors="coerce")

    async def interpret_urbanization_value(
        self, landuse_polygons: gpd.GeoDataFrame
    ) -> gpd.GeoDataFrame:
        """
        Build human-readable explanation for 'Уровень урбанизации'.

        The buckets are aligned with the urbanization logic:
        NaN/0, <10, <15, <30, <70, <90, >=90 + special/high-rise overrides.
        """
        required_columns = [
            "landuse_zone",
            "Многоэтажная",
            "Среднеэтажная",
            "Процент профильных объектов",
        ]
        self._validator.ensure(landuse_polygons, required_columns)

        logger.debug("Interpreting urbanization explanation for %d rows.", len(landuse_polygons))

        zone = landuse_polygons["landuse_zone"]
        highrise = self._to_numeric_series(landuse_polygons, "Многоэтажная")
        midrise = self._to_numeric_series(landuse_polygons, "Среднеэтажная")
        share = self._to_numeric_series(landuse_polygons, "Процент профильных объектов")

        is_residential = zone.eq("Residential")
        is_special = zone.eq("Special")

        conditions = [
            (is_residential & (highrise > 30.0)),
            (is_residential & (midrise > 30.0)),
            is_special,
            share.isna(),
            share.eq(0.0),
            share.lt(self._t.low),
            share.lt(self._t.weak),
            share.lt(self._t.medium),
            share.lt(self._t.good),
            share.lt(self._t.high),
            share.ge(self._t.high),
        ]

        explanations = [
            "На территории доминирует многоэтажный тип застройки, что делает уровень урбанизации высоким",
            "На территории доминирует среднеэтажный тип застройки, что делает уровень урбанизации высоким",
            "На территории расположены объекты специального назначения, что делает уровень урбанизации высоким",
            "На территории нет профильных объектов",
            "На территории нет профильных объектов",
            "Профильные объекты занимают <10% площади территории",
            "Профильные объекты занимают <15% площади территории",
            "Профильные объекты занимают <30% площади территории",
            "Профильные объекты занимают <70% площади территории",
            "Профильные объекты занимают 70–90% площади территории",
            "Профильные объекты занимают ≥90% площади территории",
        ]

        landuse_polygons["Пояснение уровня урбанизации"] = np.select(
            conditions,
            explanations,
            default="На территории нет профильных объектов",
        )
        return landuse_polygons

    async def interpret_renovation_value(
        self, landuse_polygons: gpd.GeoDataFrame
    ) -> gpd.GeoDataFrame:
        """
        Interpret renovation potential explanation using the same share thresholds.

        Notes:
        - Converted => always 'not subject to renovation' due to influence zone.
        - Special/high-urbanized => effective / not subject to renovation.
        - Low share / no data => renovation.
        """
        required_columns = [
            "Converted",
            "landuse_zone",
            "Многоэтажная",
            "Среднеэтажная",
            "Уровень урбанизации",
            "Процент профильных объектов",
        ]
        self._validator.ensure(landuse_polygons, required_columns)

        logger.debug("Interpreting renovation explanation for %d rows.", len(landuse_polygons))

        zone = landuse_polygons["landuse_zone"]
        highrise = self._to_numeric_series(landuse_polygons, "Многоэтажная")
        midrise = self._to_numeric_series(landuse_polygons, "Среднеэтажная")
        share = self._to_numeric_series(landuse_polygons, "Процент профильных объектов")

        is_converted = landuse_polygons["Converted"].fillna(False).astype(bool)
        is_special = zone.eq("Special")

        is_high_urbanization = (
            landuse_polygons["Уровень урбанизации"].eq("Высоко урбанизированная территория")
            | (zone.eq("Residential") & ((highrise > 30.0) | (midrise > 30.0)))
            | is_special
        )

        conditions = [
            is_converted,
            is_special,
            is_high_urbanization,
            share.isna(),
            share.eq(0.0),
            share.lt(self._t.low),
            share.lt(self._t.weak),
            share.lt(self._t.medium),
            share.lt(self._t.good),
            share.lt(self._t.high),
            share.ge(self._t.high),
        ]

        explanations = [
            "Территория не подлежит реновации, так как находится в зоне влияния высоко урбанизированной территории",
            "На территории находятся объекты специального назначения не подлежащие реновации",
            "Территория используется эффективно и не подлежит реновации",
            "Территория используется неэффективно и подлежит реновации",
            "Территория используется неэффективно и подлежит реновации",
            "Территория используется неэффективно и подлежит реновации",
            "Территория используется неэффективно и подлежит реновации",
            "Территория используется эффективно и не подлежит реновации",
            "Территория используется эффективно и не подлежит реновации",
            "Территория используется эффективно и не подлежит реновации",
            "Территория используется эффективно и не подлежит реновации",
        ]

        landuse_polygons["Пояснение потенциала реновации"] = np.select(
            conditions,
            explanations,
            default="Территория используется неэффективно и подлежит реновации",
        )
        return landuse_polygons


interpretation_service = InterpretationService()
