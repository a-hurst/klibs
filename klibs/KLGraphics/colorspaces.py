# Define the color lists for different colour spaces, in order to avoid extra dependencies and 
# performance costs. May switch to just requiring colormath in future.
rgb = []
for i in range(0, 256):
	rgb.append((255-i, i ,0, 255))
for i in range(1, 256):
	rgb.append((0, 255-i, 0+i, 255))
for i in range(1, 255):
	rgb.append((0+i, 0, 255-i, 255))

const_lum = [(211, 63, 106, 255), (210, 64, 104, 255), (210, 65, 101, 255), (209, 66, 99, 255), 
		     (209, 67, 96, 255), (208, 68, 94, 255), (208, 69, 91, 255), (207, 70, 89, 255), 
		     (207, 71, 86, 255), (206, 72, 84, 255), (206, 73, 81, 255), (205, 74, 78, 255),
		     (205, 75, 75, 255), (204, 75, 72, 255), (203, 76, 69, 255), (203, 77, 66, 255), 
		     (202, 78, 63, 255), (202, 79, 59, 255), (201, 80, 56, 255), (200, 81, 52, 255), 
		     (200, 82, 48, 255), (199, 82, 43, 255), (198, 83, 39, 255), (198, 84, 33, 255),
		     (197, 85, 27, 255), (196, 86, 19, 255), (195, 87, 7, 255), (195, 87, 0, 255), 
		     (194, 88, 0, 255), (193, 89, 0, 255), (192, 90, 0, 255), (191, 91, 0, 255), 
		     (191, 91, 0, 255), (190, 92, 0, 255), (189, 93, 0, 255), (188, 94, 0, 255),
		     (187, 95, 0, 255), (186, 95, 0, 255), (185, 96, 0, 255), (184, 97, 0, 255), 
		     (183, 98, 0, 255), (183, 98, 0, 255), (182, 99, 0, 255), (181, 100, 0, 255), 
		     (180, 100, 0, 255), (179, 101, 0, 255), (178, 102, 0, 255), (177, 103, 0, 255),
		     (176, 103, 0, 255), (175, 104, 0, 255), (174, 105, 0, 255), (172, 105, 0, 255), 
		     (171, 106, 0, 255), (170, 107, 0, 255), (169, 107, 0, 255), (168, 108, 0, 255), 
		     (167, 109, 0, 255), (166, 109, 0, 255), (165, 110, 0, 255), (164, 111, 0, 255),
		     (162, 111, 0, 255), (161, 112, 0, 255), (160, 112, 0, 255), (159, 113, 0, 255), 
		     (157, 114, 0, 255), (156, 114, 0, 255), (155, 115, 0, 255), (154, 115, 0, 255), 
		     (152, 116, 0, 255), (151, 117, 0, 255), (150, 117, 0, 255), (148, 118, 0, 255),
		     (147, 118, 0, 255), (146, 119, 0, 255), (144, 119, 0, 255), (143, 120, 0, 255), 
		     (141, 120, 0, 255), (140, 121, 0, 255), (138, 122, 0, 255), (137, 122, 0, 255), 
		     (135, 123, 0, 255), (134, 123, 0, 255), (132, 124, 0, 255), (130, 124, 0, 255),
		     (129, 125, 0, 255), (127, 125, 0, 255), (125, 126, 0, 255), (124, 126, 0, 255), 
		     (122, 127, 0, 255), (120, 127, 0, 255), (118, 128, 0, 255), (116, 128, 0, 255), 
		     (115, 129, 0, 255), (113, 129, 0, 255), (111, 130, 0, 255), (109, 130, 0, 255),
		     (107, 130, 0, 255), (104, 131, 0, 255), (102, 131, 0, 255), (100, 132, 0, 255), 
		     (98, 132, 0, 255), (95, 133, 0, 255), (93, 133, 0, 255), (90, 134, 0, 255), 
		     (88, 134, 0, 255), (85, 134, 0, 255), (82, 135, 0, 255), (79, 135, 0, 255),
		     (76, 136, 0, 255), (73, 136, 0, 255), (70, 137, 0, 255), (66, 137, 0, 255), 
		     (63, 137, 0, 255), (59, 138, 0, 255), (54, 138, 0, 255), (49, 138, 0, 255), 
		     (44, 139, 0, 255), (38, 139, 0, 255), (31, 140, 0, 255), (21, 140, 0, 255),
		     (6, 140, 0, 255), (0, 141, 0, 255), (0, 141, 0, 255), (0, 141, 0, 255), 
		     (0, 142, 0, 255), (0, 142, 0, 255), (0, 142, 0, 255), (0, 143, 0, 255), 
		     (0, 143, 0, 255), (0, 143, 0, 255), (0, 144, 0, 255), (0, 144, 0, 255),
		     (0, 144, 0, 255), (0, 145, 0, 255), (0, 145, 0, 255), (0, 145, 0, 255), 
		     (0, 146, 0, 255), (0, 146, 0, 255), (0, 146, 0, 255), (0, 146, 0, 255), 
		     (0, 147, 4, 255), (0, 147, 17, 255), (0, 147, 25, 255), (0, 147, 31, 255),
		     (0, 148, 37, 255), (0, 148, 41, 255), (0, 148, 46, 255), (0, 148, 50, 255), 
		     (0, 149, 53, 255), (0, 149, 57, 255), (0, 149, 60, 255), (0, 149, 63, 255), 
		     (0, 150, 67, 255), (0, 150, 70, 255), (0, 150, 72, 255), (0, 150, 75, 255),
		     (0, 150, 78, 255), (0, 151, 80, 255), (0, 151, 83, 255), (0, 151, 86, 255), 
		     (0, 151, 88, 255), (0, 151, 90, 255), (0, 151, 93, 255), (0, 152, 95, 255), 
		     (0, 152, 97, 255), (0, 152, 100, 255), (0, 152, 102, 255), (0, 152, 104, 255), 
		     (0, 152, 106, 255), (0, 152, 108, 255), (0, 152, 110, 255), (0, 152, 113, 255), 
		     (0, 153, 115, 255), (0, 153, 117, 255), (0, 153, 119, 255), (0, 153, 121, 255), 
		     (0, 153, 123, 255), (0, 153, 125, 255), (0, 153, 127, 255), (0, 153, 128, 255), 
		     (0, 153, 130, 255), (0, 153, 132, 255), (0, 153, 134, 255), (0, 153, 136, 255), 
		     (0, 153, 138, 255), (0, 153, 140, 255), (0, 153, 141, 255), (0, 153, 143, 255), 
		     (0, 153, 145, 255), (0, 153, 147, 255), (0, 153, 149, 255), (0, 152, 150, 255), 
		     (0, 152, 152, 255), (0, 152, 154, 255), (0, 152, 155, 255), (0, 152, 157, 255), 
		     (0, 152, 159, 255), (0, 152, 161, 255), (0, 152, 162, 255), (0, 151, 164, 255), 
		     (0, 151, 165, 255), (0, 151, 167, 255), (0, 151, 169, 255), (0, 151, 170, 255), 
		     (0, 150, 172, 255), (0, 150, 173, 255), (0, 150, 175, 255), (0, 150, 176, 255), 
		     (0, 149, 178, 255), (0, 149, 179, 255), (0, 149, 181, 255), (0, 148, 182, 255), 
		     (0, 148, 184, 255), (0, 148, 185, 255), (0, 147, 187, 255), (0, 147, 188, 255), 
		     (0, 146, 189, 255), (0, 146, 191, 255), (0, 145, 192, 255), (0, 145, 193, 255), 
		     (0, 145, 195, 255), (0, 144, 196, 255), (0, 144, 197, 255), (0, 143, 198, 255), 
		     (0, 142, 200, 255), (0, 142, 201, 255), (0, 141, 202, 255), (0, 141, 203, 255), 
		     (0, 140, 204, 255), (0, 140, 205, 255), (0, 139, 207, 255), (0, 138, 208, 255), 
		     (0, 138, 209, 255), (0, 137, 210, 255), (0, 136, 211, 255), (0, 135, 212, 255), 
		     (0, 135, 213, 255), (0, 134, 214, 255), (0, 133, 214, 255), (0, 132, 215, 255), 
		     (0, 131, 216, 255), (0, 131, 217, 255), (0, 130, 218, 255), (0, 129, 219, 255), 
		     (0, 128, 219, 255), (0, 127, 220, 255), (0, 126, 221, 255), (0, 125, 221, 255), 
		     (0, 124, 222, 255), (0, 123, 222, 255), (0, 122, 223, 255), (0, 121, 224, 255), 
		     (0, 120, 224, 255), (0, 119, 224, 255), (4, 118, 225, 255), (29, 117, 225, 255), 
		     (42, 116, 226, 255), (52, 115, 226, 255), (61, 114, 226, 255), (68, 112, 227, 255), 
		     (74, 111, 227, 255), (80, 110, 227, 255), (86, 109, 227, 255), (91, 108, 227, 255), 
		     (96, 106, 227, 255), (100, 105, 227, 255), (105, 104, 227, 255), (109, 103, 227, 255), 
		     (113, 101, 227, 255), (116, 100, 227, 255), (120, 99, 227, 255), (124, 97, 227, 255), 
		     (127, 96, 227, 255), (130, 95, 227, 255), (133, 93, 226, 255), (137, 92, 226, 255), 
		     (139, 91, 226, 255), (142, 89, 225, 255), (145, 88, 225, 255), (148, 86, 224, 255), 
		     (150, 85, 224, 255), (153, 84, 224, 255), (156, 82, 223, 255), (158, 81, 222, 255), 
		     (160, 79, 222, 255), (163, 78, 221, 255), (165, 77, 221, 255), (167, 75, 220, 255), 
		     (169, 74, 219, 255), (171, 72, 218, 255), (173, 71, 218, 255), (175, 70, 217, 255), 
		     (177, 68, 216, 255), (178, 67, 215, 255), (180, 65, 214, 255), (182, 64, 213, 255), 
		     (183, 63, 212, 255), (185, 61, 211, 255), (187, 60, 210, 255), (188, 59, 209, 255), 
		     (189, 58, 208, 255), (191, 56, 207, 255), (192, 55, 206, 255), (193, 54, 205, 255), 
		     (195, 53, 204, 255), (196, 52, 202, 255), (197, 51, 201, 255), (198, 49, 200, 255), 
		     (199, 48, 199, 255), (200, 47, 197, 255), (201, 46, 196, 255), (202, 46, 195, 255), 
		     (203, 45, 193, 255), (204, 44, 192, 255), (205, 43, 190, 255), (205, 43, 189, 255), 
		     (206, 42, 188, 255), (207, 41, 186, 255), (208, 41, 185, 255), (208, 40, 183, 255), 
		     (209, 40, 182, 255), (209, 40, 180, 255), (210, 40, 178, 255), (210, 39, 177, 255), 
		     (211, 39, 175, 255), (211, 39, 174, 255), (212, 39, 172, 255), (212, 39, 170, 255), 
		     (213, 40, 169, 255), (213, 40, 167, 255), (213, 40, 165, 255), (213, 40, 163, 255), 
		     (214, 41, 162, 255), (214, 41, 160, 255), (214, 42, 158, 255), (214, 42, 156, 255), 
		     (214, 43, 155, 255), (214, 44, 153, 255), (214, 44, 151, 255), (215, 45, 149, 255), 
		     (215, 46, 147, 255), (215, 46, 145, 255), (215, 47, 143, 255), (214, 48, 142, 255), 
		     (214, 49, 140, 255), (214, 50, 138, 255), (214, 50, 136, 255), (214, 51, 134, 255), 
		     (214, 52, 132, 255), (214, 53, 130, 255), (214, 54, 128, 255), (213, 55, 126, 255), 
		     (213, 56, 123, 255), (213, 57, 121, 255), (213, 58, 119, 255), (212, 59, 117, 255), 
		     (212, 60, 115, 255), (212, 61, 113, 255), (211, 62, 110, 255), (211, 62, 108, 255)]