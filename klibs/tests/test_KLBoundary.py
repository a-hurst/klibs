# -*- coding: utf-8 -*-
import pytest

import klibs
from klibs import KLBoundary as klb


def test_rectangle_boundary():

    rect = klb.RectangleBoundary('test1', p1=(10, 10), p2=(50, 50))

    # Test position arguments and boundaries with floats
    pos = klb.RectangleBoundary('test2', (10, 10), (50, 50))
    floats = klb.RectangleBoundary('test3', p1=(10.4, 10.8), p2=(50.5, 50.2))

    # Test string
    assert str(rect) == "RectangleBoundary(p1=(10, 10), p2=(50, 50))"

    # Test boundary attributes
    assert rect.label == 'test1'
    assert rect.p1 == (10, 10)
    assert rect.p2 == (50, 50)
    assert rect.center == (30, 30)

    # Test boundary usage
    assert rect.within((0, 0)) == False
    assert rect.within((100, 30)) == False
    assert rect.within((35.3, 35)) == True
    assert rect.within((10, 10)) == True
    assert rect.within((50, 50)) == True
    assert (10, 10) in rect
    assert not (0, 0) in rect

    # Test boundary exceptions
    with pytest.raises(ValueError):
        rect.within(5)
    with pytest.raises(ValueError):
        klb.RectangleBoundary('test4', p1=(60, 60), p2=(50, 50))
    with pytest.raises(ValueError):
        klb.RectangleBoundary('test5', p1=0, p2=(50, 50))


def test_circle_boundary():

    circle = klb.CircleBoundary('test1', center=(100, 100), radius=50)

    # Test position arguments and boundaries with floats
    pos = klb.CircleBoundary('test2', (100, 100), 50)
    floats = klb.CircleBoundary('test3', center=(99.5, 100), radius=43.5)

    # Test string
    assert str(circle) == "CircleBoundary(center=(100, 100), radius=50)"

    # Test boundary attributes
    assert circle.label == 'test1'
    assert circle.center == (100, 100)
    assert circle.radius == 50

    # Test boundary usage
    assert circle.within((0, 0)) == False
    assert circle.within((1000, 100)) == False
    assert circle.within((51, 51)) == False
    assert circle.within((99.7, 100)) == True
    assert circle.within((50, 100)) == True
    assert circle.within((100, 150)) == True
    assert (50, 100) in circle
    assert not (0, 0) in circle

    # Test boundary exceptions
    with pytest.raises(ValueError):
        circle.within(5)
    with pytest.raises(ValueError):
        klb.CircleBoundary('test4', center=(100, 100), radius=-4)
    with pytest.raises(ValueError):
        klb.CircleBoundary('test5', center=100, radius=50)

    
def test_annulus_boundary():

    ring = klb.AnnulusBoundary('test1', center=(100, 100), radius=50, thickness=10)

    # Test position arguments and boundaries with floats
    pos = klb.AnnulusBoundary('test2', (100, 100), 50, 10)
    floats = klb.AnnulusBoundary('test3', center=(99.5, 100), radius=43.5, thickness=4.6)

    # Test string
    assert str(ring) == "AnnulusBoundary(center=(100, 100), radius=50, thickness=10)"

    # Test boundary attributes
    assert ring.label == 'test1'
    assert ring.center == (100, 100)
    assert ring.thickness == 10
    assert ring.outer_radius == 50
    assert ring.inner_radius == 40

    # Test boundary usage
    assert ring.within((0, 0)) == False
    assert ring.within((1000, 100)) == False
    assert ring.within((51, 51)) == False
    assert ring.within((100, 100)) == False
    assert ring.within((61, 100)) == False
    assert ring.within((55.5, 100)) == True
    assert ring.within((50, 100)) == True
    assert ring.within((60, 100)) == True
    assert ring.within((100, 150)) == True
    assert ring.within((100, 140)) == True
    assert (55, 100) in ring
    assert not (0, 0) in ring

    # Test boundary exceptions
    with pytest.raises(ValueError):
        ring.within(5)
    with pytest.raises(ValueError):
        klb.AnnulusBoundary('test4', center=(100, 100), radius=-4, thickness=10)
    with pytest.raises(ValueError):
        klb.AnnulusBoundary('test5', center=(100, 100), radius=50, thickness=-5)
    with pytest.raises(ValueError):
        klb.AnnulusBoundary('test6', center=(100, 100), radius=10, thickness=30)
    with pytest.raises(ValueError):
        klb.AnnulusBoundary('test7', center=100, radius=50, thickness=10)


def test_boundary_inspector():

    inspector = klb.BoundaryInspector()
    tst1 = klb.RectangleBoundary('test1', p1=(10, 10), p2=(50, 50))
    tst2 = klb.RectangleBoundary('test2', p1=(60, 60), p2=(100, 100))
    tst3 = klb.RectangleBoundary('test3', p1=(10, 30), p2=(50, 70))

    # Test legacy method of adding boundaries to inspector
    rect_legacy = ['legacy_rect', ((10, 10), (50, 50)), klibs.RECT_BOUNDARY]
    circle_legacy = ['legacy_circle', ((100, 10), 50), klibs.CIRCLE_BOUNDARY]
    ring_legacy = ['legacy_ring', ((100, 10), 50, 10), klibs.ANNULUS_BOUNDARY]
    for b in [rect_legacy, circle_legacy, ring_legacy]:
        inspector.add_boundary(*b)
    assert len(inspector.boundaries) == 3

    # Test legacy method of adding multiple boundaries to inspector
    inspector = klb.BoundaryInspector()
    inspector.add_boundaries([rect_legacy, circle_legacy, ring_legacy])
    assert len(inspector.boundaries) == 3

    # Test current method of adding boundaries to inspector
    inspector = klb.BoundaryInspector()
    inspector.add_boundary(tst1)
    assert len(inspector.boundaries) == 1
    inspector.add_boundaries([tst2, tst3])
    assert len(inspector.boundaries) == 3

    # Test removing boundaries from the inspector
    inspector = klb.BoundaryInspector([tst1, tst2, tst3])
    assert len(inspector.boundaries) == 3
    inspector.remove_boundaries('test1')
    assert len(inspector.boundaries) == 2
    inspector.remove_boundaries(['test2', 'test3'])
    assert len(inspector.boundaries) == 0

    # Test clearing boundaries from the inspector
    inspector = klb.BoundaryInspector()
    inspector.add_boundaries([tst1, tst2, tst3])
    inspector.clear_boundaries()
    assert len(inspector.boundaries) == 0
    inspector.add_boundaries([tst1, tst2, tst3])
    inspector.clear_boundaries(preserve=['test2'])
    assert len(inspector.boundaries) == 1
    assert 'test2' in inspector.labels

    # Test individual boundary tests
    inspector = klb.BoundaryInspector()
    inspector.add_boundaries([tst1, tst2, tst3])
    assert inspector.within_boundary('test1', (20, 40)) == True
    assert inspector.within_boundary('test2', (20, 40)) == False
    assert inspector.within_boundary('test3', (20, 40)) == True

    # Test combined boundary tests
    inspector = klb.BoundaryInspector()
    inspector.add_boundaries([tst1, tst2, tst3])
    assert inspector.which_boundary((20, 40)) == 'test3'
    assert inspector.which_boundary((20, 40), ignore='test3') == 'test1'
    assert inspector.which_boundary((20, 40), ignore=['test3']) == 'test1'
    assert inspector.which_boundary((20, 40), labels=['test1', 'test2']) == 'test1'
    assert inspector.which_boundary((20, 40), labels=['test2']) == None

    # Test exceptions
    inspector = klb.BoundaryInspector()
    with pytest.raises(ValueError):
        inspector.add_boundary('hello')
    with pytest.raises(ValueError):
        inspector.add_boundary('test', [(80, 80), 15], shape="Triangle")
    with pytest.raises(KeyError):
        inspector.within_boundary('hello', (80, 80))
    