// Boat Puck — GoPro HERO9–13 housing
// Doctrine: housing cavity = camera positive (mold clearance = microns).
// Units: mm
//
// camera_positive()  — exact published chassis (use as cavity / insert outer)
// print_slip_dummy() — optional −0.15 mm/side for FDM drop-fit only

/* [Camera positive = cavity] */
cam_W = 71.8;
cam_H = 50.8;
cam_D = 33.6;

/* [Optional FDM slip — NOT cavity uncertainty] */
slip_per_side = 0.15;
slip_depth_total = 0.30;

$fn = 64;

module camera_positive() {
  // Bounding box of HERO9–13 per GoPro product specs.
  // Real camera is not a perfect box (lens, fingers, doors) —
  // replace with official STEP when available; this is the envelope.
  cube([cam_W, cam_H, cam_D], center = true);
}

module print_slip_dummy() {
  cube([
    cam_W - 2 * slip_per_side,
    cam_H - 2 * slip_per_side,
    cam_D - slip_depth_total
  ], center = true);
}

// Front marker (−Z = lens) for orientation when printing
module marked_positive() {
  difference() {
    camera_positive();
    translate([0, cam_H / 2 - 1.2, -cam_D / 2 + 1.0])
      cube([10, 2.4, 2], center = true);
  }
}

// Default preview: exact cavity/camera solid
color([0.2, 0.55, 0.95, 0.55]) camera_positive();

// Uncomment to export STL:
// marked_positive();
// print_slip_dummy();

echo(str("CAVITY = CAMERA positive mm: ", cam_W, " x ", cam_H, " x ", cam_D));
echo(str("volume cm3: ", cam_W * cam_H * cam_D / 1000));
