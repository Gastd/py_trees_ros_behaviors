#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: BSD
#   https://github.com/splintered-reality/py_trees_ros_behaviors/raw/devel/LICENSE
#
##############################################################################
# Documentation
##############################################################################
"""
Tutorial 5 - Action Clients
"""
##############################################################################
# Imports
##############################################################################

import py_trees_ros_behaviors.five_action_clients as tutorial

##############################################################################
# Launch Service
##############################################################################


def generate_launch_description():
    """
    Launch description for the tutorial.
    """
    return tutorial.generate_launch_description()
